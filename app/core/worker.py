"""
后台工作线程 - 任务执行的"引擎"和"指挥中心"
"""

import threading
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .models import Mission, MissionStatus, SubtaskStatus
from .mission_manager import MissionManager
from .queue_manager import QueueManager
from .config_manager import ConfigManager
from .tool_manager import ToolManager
from .llm_manager import LLMManager
from .report_generator import ReportGenerator
from .notification_manager import NotificationManager
from ..agents.agent_factory import AgentFactory

logger = logging.getLogger(__name__)


class Worker:
    """后台工作线程 - 驱动任务从PENDING到COMPLETED的整个生命周期"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.mission_manager = MissionManager()
        self.queue_manager = QueueManager()
        self.tool_manager = ToolManager(config_manager)
        self.llm_manager = LLMManager(config_manager)
        self.report_generator = ReportGenerator(config_manager)
        self.notification_manager = NotificationManager(config_manager)
        self.agent_factory = AgentFactory(self.tool_manager, self.llm_manager)
        
        # 工作线程控制
        self.running = False
        self.worker_thread = None
        
        # 配置参数
        self.check_interval = config_manager.get('system.queue_check_interval', 5)
        self.max_retries = config_manager.get('system.max_retries', 3)
        self.task_timeout = config_manager.get('system.task_timeout', 3600)
        
        logger.info("Worker初始化完成")
    
    def start(self):
        """启动工作线程"""
        if self.running:
            logger.warning("Worker已在运行")
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Worker线程启动")
    
    def stop(self):
        """停止工作线程"""
        if not self.running:
            return
        
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        logger.info("Worker线程停止")
    
    def run(self):
        """运行Worker（阻塞方式）"""
        self.running = True
        self._worker_loop()
    
    def _worker_loop(self):
        """工作线程主循环"""
        logger.info("Worker开始工作循环")
        
        # 启动时恢复孤儿任务
        self.queue_manager.recover_orphaned_tasks()
        
        while self.running:
            try:
                # 检查是否有待处理的任务
                if not self.queue_manager.has_pending_tasks():
                    time.sleep(self.check_interval)
                    continue
                
                # 获取下一个任务
                mission_id = self.queue_manager.dequeue()
                if not mission_id:
                    time.sleep(self.check_interval)
                    continue
                
                # 处理任务
                self._process_mission(mission_id)
                
            except Exception as e:
                logger.error(f"Worker循环出错: {e}")
                time.sleep(self.check_interval)
    
    def _process_mission(self, mission_id: str):
        """处理单个任务"""
        try:
            logger.info(f"开始处理任务: {mission_id}")
            
            # 加载任务
            mission = self.mission_manager.get_mission(mission_id)
            if not mission:
                logger.error(f"任务不存在: {mission_id}")
                self.queue_manager.mark_failed(mission_id, {"error": "任务不存在"})
                return
            
            # 检查任务状态
            if mission.status != MissionStatus.PENDING:
                logger.warning(f"任务状态异常: {mission_id} - {mission.status}")
                return
            
            # 执行任务
            success = self._execute_mission(mission)
            
            # 更新队列状态
            if success:
                self.queue_manager.mark_completed(mission_id)
            else:
                self.queue_manager.mark_failed(mission_id, {"error": mission.error_message})
            
        except Exception as e:
            error_message = f"处理任务异常 {mission_id}: {e}"
            logger.error(error_message)
            self.queue_manager.mark_failed(mission_id, {"error": error_message})
    
    def _execute_mission(self, mission: Mission) -> bool:
        """执行任务的主要逻辑"""
        try:
            # 阶段1: 规划
            if not self._planning_phase(mission):
                return False
            
            # 阶段2: 执行
            if not self._execution_phase(mission):
                return False
            
            # 阶段3: 报告总结
            if not self._reporting_phase(mission):
                return False
            
            # 阶段4: 渲染报告
            if not self._rendering_phase(mission):
                return False
            
            # 阶段5: 通知推送
            if not self._notification_phase(mission):
                return False
            
            # 完成
            mission.update_status(MissionStatus.COMPLETED)
            self.mission_manager.update_mission(mission)
            
            logger.info(f"任务执行完成: {mission.mission_id}")
            return True
            
        except Exception as e:
            error_message = f"任务执行失败: {e}"
            logger.error(error_message)
            mission.update_status(MissionStatus.FAILED, error_message)
            self.mission_manager.update_mission(mission)
            return False
    
    def _planning_phase(self, mission: Mission) -> bool:
        """规划阶段"""
        try:
            logger.info(f"进入规划阶段: {mission.mission_id}")
            mission.update_status(MissionStatus.PLANNING)
            self.mission_manager.update_mission(mission)
            
            # 调用编排Agent
            orchestrator = self.agent_factory.get_agent('OrchestratorAgent')
            if not orchestrator:
                raise Exception("无法创建OrchestratorAgent")
            
            result = orchestrator.execute(mission.natural_language_goal)
            
            if result['status'] != 'success':
                raise Exception(f"任务规划失败: {result.get('error', '未知错误')}")
            
            # 更新子任务图
            analysis_data = result['data']
            subtasks = analysis_data.get('subtasks', [])
            
            mission.subtask_graph = []
            for subtask_data in subtasks:
                mission.add_subtask(
                    subagent_name=subtask_data['subagent_name'],
                    goal=subtask_data['goal'],
                    dependencies=subtask_data['dependencies']
                )
            
            self.mission_manager.update_mission(mission)
            logger.info(f"规划完成，生成{len(mission.subtask_graph)}个子任务")
            
            return True
            
        except Exception as e:
            error_message = f"规划阶段失败: {e}"
            logger.error(error_message)
            mission.update_status(MissionStatus.FAILED, error_message)
            self.mission_manager.update_mission(mission)
            return False
    
    def _execution_phase(self, mission: Mission) -> bool:
        """执行阶段"""
        try:
            logger.info(f"进入执行阶段: {mission.mission_id}")
            mission.update_status(MissionStatus.EXECUTING)
            self.mission_manager.update_mission(mission)
            
            # 循环执行子任务直到完成或失败
            max_iterations = len(mission.subtask_graph) * 2  # 防止无限循环
            iteration = 0
            
            while not mission.is_all_subtasks_completed() and iteration < max_iterations:
                iteration += 1
                
                # 获取可执行的子任务
                ready_subtasks = mission.get_ready_subtasks()
                
                if not ready_subtasks:
                    # 检查是否有失败的子任务
                    if mission.has_failed_subtasks():
                        raise Exception("存在失败的子任务")
                    
                    # 没有可执行的任务，可能存在循环依赖
                    if mission.get_pending_subtasks():
                        raise Exception("检测到循环依赖或无法满足的依赖")
                    
                    break
                
                # 执行就绪的子任务
                for subtask in ready_subtasks:
                    self._execute_subtask(mission, subtask)
                    self.mission_manager.update_mission(mission)
                
                time.sleep(1)  # 短暂延迟
            
            if not mission.is_all_subtasks_completed():
                raise Exception("子任务执行未完成")
            
            logger.info(f"执行阶段完成: {mission.mission_id}")
            return True
            
        except Exception as e:
            error_message = f"执行阶段失败: {e}"
            logger.error(error_message)
            mission.update_status(MissionStatus.FAILED, error_message)
            self.mission_manager.update_mission(mission)
            return False
    
    def _execute_subtask(self, mission: Mission, subtask):
        """执行单个子任务"""
        try:
            logger.info(f"执行子任务: {subtask.subtask_id} - {subtask.goal}")
            
            # 更新子任务状态
            mission.update_subtask_status(subtask.subtask_id, SubtaskStatus.IN_PROGRESS)
            
            # 获取对应的Agent
            agent = self.agent_factory.get_agent(subtask.subagent_name)
            if not agent:
                raise Exception(f"无法创建Agent: {subtask.subagent_name}")
            
            # 准备上下文
            context = {
                'mission_id': mission.mission_id,
                'mission_data': mission.to_dict(),
                'subtask_id': subtask.subtask_id
            }
            
            # 执行Agent
            result = agent.execute(subtask.goal, context)
            
            if result['status'] == 'success':
                mission.update_subtask_status(
                    subtask.subtask_id, 
                    SubtaskStatus.COMPLETED,
                    result=result.get('data')
                )
                logger.info(f"子任务完成: {subtask.subtask_id}")
            else:
                error_message = result.get('error', '未知错误')
                mission.update_subtask_status(
                    subtask.subtask_id,
                    SubtaskStatus.FAILED,
                    error_message=error_message
                )
                logger.error(f"子任务失败: {subtask.subtask_id} - {error_message}")
                
        except Exception as e:
            error_message = f"子任务执行异常: {e}"
            logger.error(error_message)
            mission.update_subtask_status(
                subtask.subtask_id,
                SubtaskStatus.FAILED,
                error_message=error_message
            )
    
    def _reporting_phase(self, mission: Mission) -> bool:
        """报告总结阶段"""
        try:
            logger.info(f"进入报告阶段: {mission.mission_id}")
            mission.update_status(MissionStatus.REPORTING)
            self.mission_manager.update_mission(mission)
            
            # 调用ReportAgent生成总结
            report_agent = self.agent_factory.get_agent('ReportAgent')
            if not report_agent:
                raise Exception("无法创建ReportAgent")
            
            context = {'mission_data': mission.to_dict()}
            result = report_agent.execute("生成任务总结", context)
            
            if result['status'] == 'success':
                mission.final_summary = result['data'].get('summary', '')
                self.mission_manager.update_mission(mission)
                logger.info(f"报告阶段完成: {mission.mission_id}")
            else:
                logger.warning(f"报告生成失败，使用默认总结: {result.get('error')}")
                mission.final_summary = f"任务完成: {mission.natural_language_goal}"
                self.mission_manager.update_mission(mission)
            
            return True
            
        except Exception as e:
            logger.error(f"报告阶段失败: {e}")
            mission.final_summary = f"任务完成: {mission.natural_language_goal}"
            self.mission_manager.update_mission(mission)
            return True  # 报告失败不影响任务完成
    
    def _rendering_phase(self, mission: Mission) -> bool:
        """渲染报告阶段"""
        try:
            # 检查是否需要生成报告
            if not mission.report_config:
                logger.info(f"跳过渲染阶段（无需生成报告）: {mission.mission_id}")
                return True
            
            logger.info(f"进入渲染阶段: {mission.mission_id}")
            mission.update_status(MissionStatus.RENDERING)
            self.mission_manager.update_mission(mission)
            
            # 使用ReportGenerator生成HTML报告
            try:
                template_name = mission.report_config.get('template', 'mission_report.html')
                report_path = self.report_generator.generate_report(mission, template_name)
                
                # 生成访问URL
                report_url = self.report_generator.generate_report_url(mission.mission_id)
                mission.result_page_url = report_url
                
                # 保存报告路径到任务数据
                if not hasattr(mission, 'report_path'):
                    mission.report_path = report_path
                
                self.mission_manager.update_mission(mission)
                logger.info(f"报告生成成功: {report_path}")
                
            except Exception as e:
                logger.error(f"报告生成失败: {e}")
                # 设置默认URL，不影响任务完成
                mission.result_page_url = f"/results/{mission.mission_id}.html"
                self.mission_manager.update_mission(mission)
            
            logger.info(f"渲染阶段完成: {mission.mission_id}")
            return True
            
        except Exception as e:
            logger.error(f"渲染阶段失败: {e}")
            return True  # 渲染失败不影响任务完成
    
    def _notification_phase(self, mission: Mission) -> bool:
        """通知推送阶段"""
        try:
            # 检查是否需要发送通知
            if not mission.notification_configs:
                logger.info(f"跳过通知阶段（无需发送通知）: {mission.mission_id}")
                return True
            
            logger.info(f"进入通知阶段: {mission.mission_id}")
            mission.update_status(MissionStatus.NOTIFYING)
            self.mission_manager.update_mission(mission)
            
            # 使用NotificationManager发送通知
            try:
                results = self.notification_manager.send_mission_notification(
                    mission_data=mission.to_dict(),
                    notification_configs=mission.notification_configs
                )
                
                # 记录通知结果
                success_count = sum(1 for success in results.values() if success)
                total_count = len(results)
                
                logger.info(f"通知发送完成: {success_count}/{total_count} 成功")
                
                # 即使部分通知失败，也不影响任务完成
                if success_count == 0 and total_count > 0:
                    logger.warning(f"所有通知发送失败: {mission.mission_id}")
                
            except Exception as e:
                logger.error(f"通知发送异常: {e}")
                # 通知失败不影响任务完成
            
            logger.info(f"通知阶段完成: {mission.mission_id}")
            return True
            
        except Exception as e:
            logger.error(f"通知阶段失败: {e}")
            return True  # 通知失败不影响任务完成
    
    def get_worker_status(self) -> Dict[str, Any]:
        """获取Worker状态"""
        queue_status = self.queue_manager.get_queue_status()
        
        return {
            'running': self.running,
            'thread_alive': self.worker_thread and self.worker_thread.is_alive(),
            'check_interval': self.check_interval,
            'queue_status': queue_status,
            'configuration': {
                'max_retries': self.max_retries,
                'task_timeout': self.task_timeout
            }
        }