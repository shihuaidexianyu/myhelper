"""
主代理协调器
任务执行的"大脑"，在一个独立的后台线程中运行，负责编排整个任务的生命周期
"""
import logging
from typing import Dict, Any, Optional
from dataclasses import asdict

from app.core.storage_manager import StorageManager
from app.core.tool_manager import ToolManager
from app.core.notification_manager import NotificationManager
from app.agents.planner_agent import PlannerAgent
from app.agents.executor_agent import ExecutorAgent
from app.agents.reporter_agent import ReporterAgent
from app.models.data_models import Learning


class MasterAgent:
    """主代理协调器，管理任务执行的整个生命周期"""
    
    def __init__(self, task_id: str, trigger_context: Dict[str, Any], report_id: str,
                 storage_manager: StorageManager = None,
                 notification_manager: NotificationManager = None):
        self.task_id = task_id
        self.trigger_context = trigger_context
        self.report_id = report_id
        
        # 初始化管理器
        self.storage_manager = storage_manager or StorageManager()
        self.notification_manager = notification_manager or NotificationManager()
        self.tool_manager = ToolManager(self.storage_manager)
        
        self.logger = logging.getLogger(__name__)
    
    def run_full_lifecycle(self):
        """运行完整的任务生命周期"""
        self.logger.info(f"Starting task lifecycle for task {self.task_id}, report {self.report_id}")
        
        try:
            # 1. 初始化与状态更新
            self._update_status("running")
            
            # 2. 数据加载
            task, authorized_tools, learnings = self._load_data()
            
            # 3. 执行主流程
            self._execute_main_flow(task, authorized_tools, learnings)
            
        except Exception as e:
            self.logger.error(f"Unexpected error in task lifecycle: {e}", exc_info=True)
            self._handle_failure({
                "error_type": type(e).__name__,
                "message": str(e),
                "phase": "lifecycle_management"
            })
    
    def _update_status(self, status: str, additional_data: Dict[str, Any] = None):
        """更新任务状态"""
        try:
            update_data = {"status": status}
            if additional_data:
                update_data.update(additional_data)
            
            self.storage_manager.update_report(self.report_id, update_data)
            self.logger.info(f"Updated report {self.report_id} status to {status}")
        except Exception as e:
            self.logger.error(f"Failed to update status: {e}")
    
    def _load_data(self) -> tuple:
        """加载任务执行所需的数据"""
        self.logger.info("Loading task data and dependencies")
        
        # 加载任务定义
        task = self.storage_manager.get_task(self.task_id)
        if not task:
            raise ValueError(f"Task {self.task_id} not found")
        
        # 加载授权工具
        authorized_tool_ids = task.get('authorized_tool_ids', [])
        authorized_tools = self.storage_manager.get_authorized_tools(authorized_tool_ids)
        
        if not authorized_tools:
            raise ValueError(f"No authorized tools found for task {self.task_id}")
        
        # 加载相关学习经验
        learnings_data = self.storage_manager.get_learnings(limit=10)
        learnings = [self._dict_to_learning(learning_dict) for learning_dict in learnings_data]
        
        self.logger.info(f"Loaded task with {len(authorized_tools)} tools and {len(learnings)} learnings")
        return task, authorized_tools, learnings
    
    def _dict_to_learning(self, learning_dict: Dict[str, Any]) -> Learning:
        """将字典转换为Learning对象"""
        return Learning(
            learning_id=learning_dict['learning_id'],
            task_id=learning_dict['task_id'],
            category=learning_dict['category'],
            title=learning_dict['title'],
            description=learning_dict['description'],
            context=learning_dict['context'],
            created_at=learning_dict['created_at'],
            confidence_score=learning_dict.get('confidence_score', 0.5)
        )
    
    def _execute_main_flow(self, task: Dict[str, Any], authorized_tools: Dict[str, Dict], 
                          learnings: list):
        """执行主要业务流程"""
        try:
            # 1. 规划阶段
            self.logger.info("Starting planning phase")
            plan = self._execute_planning_phase(task, learnings)
            
            # 2. 执行阶段
            self.logger.info("Starting execution phase")
            execution_log = self._execute_execution_phase(plan, authorized_tools)
            
            # 3. 检查执行结果
            if execution_log.status == "failed":
                error_details = {
                    "phase": "execution",
                    "message": execution_log.final_message or "Execution failed",
                    "execution_log": asdict(execution_log)
                }
                raise Exception(f"Execution failed: {execution_log.final_message}")
            
            # 4. 报告与学习阶段
            self.logger.info("Starting reporting phase")
            self._execute_reporting_phase(plan, execution_log)
            
            # 5. 成功完成
            self._handle_success()
            
        except Exception as e:
            self.logger.error(f"Error in main flow: {e}")
            
            # 尝试从当前状态构建错误详情
            error_details = {
                "error_type": type(e).__name__,
                "message": str(e),
                "phase": "main_flow"
            }
            
            self._handle_failure(error_details)
    
    def _execute_planning_phase(self, task: Dict[str, Any], learnings: list):
        """执行规划阶段"""
        try:
            planner = PlannerAgent(task, self.trigger_context, learnings)
            plan = planner.generate_plan()
            
            # 保存计划到报告
            self.storage_manager.update_report(self.report_id, {
                "plan": asdict(plan)
            })
            
            self.logger.info(f"Planning completed with {len(plan.steps)} steps")
            return plan
            
        except Exception as e:
            self.logger.error(f"Planning phase failed: {e}")
            raise Exception(f"Planning failed: {str(e)}")
    
    def _execute_execution_phase(self, plan, authorized_tools):
        """执行执行阶段"""
        try:
            executor = ExecutorAgent(self.tool_manager)
            execution_log = executor.execute(plan, authorized_tools)
            
            # 保存执行日志到报告
            self.storage_manager.update_report(self.report_id, {
                "execution_log": asdict(execution_log)
            })
            
            self.logger.info(f"Execution completed with status: {execution_log.status}")
            return execution_log
            
        except Exception as e:
            self.logger.error(f"Execution phase failed: {e}")
            raise Exception(f"Execution failed: {str(e)}")
    
    def _execute_reporting_phase(self, plan, execution_log):
        """执行报告与学习阶段"""
        try:
            reporter = ReporterAgent(plan, execution_log)
            final_summary, new_learnings = reporter.generate_report_and_learnings()
            
            # 保存最终报告
            self.storage_manager.update_report(self.report_id, {
                "final_summary": final_summary
            })
            
            # 保存学习经验
            for learning in new_learnings:
                try:
                    self.storage_manager.save_learning(asdict(learning))
                except Exception as le:
                    self.logger.warning(f"Failed to save learning {learning.learning_id}: {le}")
            
            self.logger.info(f"Reporting completed, saved {len(new_learnings)} learnings")
            
        except Exception as e:
            self.logger.error(f"Reporting phase failed: {e}")
            # 报告阶段失败不应该影响整体成功状态，只记录警告
            self.logger.warning("Task execution succeeded but reporting phase failed")
    
    def _handle_success(self):
        """处理任务成功完成"""
        try:
            # 更新最终状态
            self._update_status("success")
            
            # 发送成功通知
            report = self.storage_manager.get_report(self.report_id)
            final_summary = report.get('final_summary', 'Task completed successfully')
            
            self.notification_manager.send_success(
                self.report_id, 
                final_summary,
                context={
                    "task_id": self.task_id,
                    "trigger_context": self.trigger_context
                }
            )
            
            self.logger.info(f"Task {self.task_id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error in success handling: {e}")
            # 即使通知失败，也不要改变成功状态
    
    def _handle_failure(self, error_details: Dict[str, Any]):
        """处理任务失败"""
        try:
            # 记录详细错误日志
            self.logger.error(f"Task {self.task_id} failed: {error_details}")
            
            # 更新失败状态
            self._update_status("failed", {"error": error_details})
            
            # 发送失败通知
            self.notification_manager.send_failure(
                self.report_id,
                error_details,
                context={
                    "task_id": self.task_id,
                    "trigger_context": self.trigger_context
                }
            )
            
            self.logger.info(f"Task {self.task_id} failure handling completed")
            
        except Exception as e:
            self.logger.error(f"Error in failure handling: {e}")
            # 如果连失败处理都失败了，至少确保状态被更新
            try:
                self.storage_manager.update_report(self.report_id, {
                    "status": "failed",
                    "error": {
                        "message": "Task failed and error handling also failed",
                        "original_error": error_details,
                        "handling_error": str(e)
                    }
                })
            except:
                self.logger.critical(f"Complete failure handling breakdown for task {self.task_id}")


def run_master_agent_task(task_id: str, trigger_context: Dict[str, Any], report_id: str,
                         storage_manager: StorageManager = None,
                         notification_manager: NotificationManager = None):
    """
    运行主代理任务的入口函数
    这个函数被ThreadPoolExecutor调用
    """
    try:
        master_agent = MasterAgent(
            task_id=task_id,
            trigger_context=trigger_context,
            report_id=report_id,
            storage_manager=storage_manager,
            notification_manager=notification_manager
        )
        
        master_agent.run_full_lifecycle()
        
    except Exception as e:
        # 如果连MasterAgent初始化都失败了，记录错误
        logger = logging.getLogger(__name__)
        logger.critical(f"Failed to initialize or run MasterAgent for task {task_id}: {e}")
        
        # 尝试更新报告状态
        try:
            storage_mgr = storage_manager or StorageManager()
            storage_mgr.update_report(report_id, {
                "status": "failed",
                "error": {
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "phase": "initialization"
                }
            })
        except:
            logger.critical(f"Could not update report {report_id} after initialization failure")