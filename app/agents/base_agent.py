"""
Agent基类 - 所有Agent的基础类
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, name: str, tool_manager, llm_manager):
        self.name = name
        self.tool_manager = tool_manager
        self.llm_manager = llm_manager
        self.logger = logging.getLogger(f"agent.{name}")
    
    @abstractmethod
    def execute(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行Agent任务
        
        Args:
            goal: 任务目标描述
            context: 任务上下文信息
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        pass
    
    def log_execution(self, goal: str, result: Dict[str, Any]):
        """记录执行日志"""
        status = result.get('status', 'unknown')
        self.logger.info(f"Agent执行完成 - 目标: {goal[:100]}... 状态: {status}")
    
    def create_error_result(self, error_message: str, error_details: Optional[Dict] = None) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            'status': 'failed',
            'error': error_message,
            'error_details': error_details or {},
            'agent': self.name
        }
    
    def create_success_result(self, data: Any, message: str = "执行成功") -> Dict[str, Any]:
        """创建成功结果"""
        return {
            'status': 'success',
            'message': message,
            'data': data,
            'agent': self.name
        }
    
    def validate_goal(self, goal: str) -> bool:
        """验证目标是否有效"""
        return bool(goal and goal.strip())


class OrchestratorAgent(BaseAgent):
    """编排Agent - 任务的"总设计师"""
    
    def __init__(self, tool_manager, llm_manager):
        super().__init__("OrchestratorAgent", tool_manager, llm_manager)
    
    def execute(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行任务规划"""
        try:
            if not self.validate_goal(goal):
                return self.create_error_result("任务目标无效")
            
            self.logger.info(f"开始规划任务: {goal}")
            
            # 使用LLM分析任务
            analysis_result = self.llm_manager.analyze_task(goal)
            
            # 验证分析结果
            if not self._validate_analysis_result(analysis_result):
                return self.create_error_result("任务分析结果格式无效")
            
            result = self.create_success_result(
                data=analysis_result,
                message="任务规划完成"
            )
            
            self.log_execution(goal, result)
            return result
            
        except Exception as e:
            error_message = f"任务规划失败: {str(e)}"
            self.logger.error(error_message)
            return self.create_error_result(error_message)
    
    def _validate_analysis_result(self, result: Dict[str, Any]) -> bool:
        """验证分析结果格式"""
        try:
            if 'subtasks' not in result:
                return False
            
            for subtask in result['subtasks']:
                required_fields = ['subtask_id', 'subagent_name', 'goal', 'dependencies']
                if not all(field in subtask for field in required_fields):
                    return False
            
            return True
        except:
            return False


class DataQueryAgent(BaseAgent):
    """数据查询Agent"""
    
    def __init__(self, tool_manager, llm_manager):
        super().__init__("DataQueryAgent", tool_manager, llm_manager)
    
    def execute(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行数据查询任务"""
        try:
            if not self.validate_goal(goal):
                return self.create_error_result("查询目标无效")
            
            self.logger.info(f"执行数据查询: {goal}")
            
            # 解析查询目标，确定要调用的服务
            service_info = self._parse_query_goal(goal, context)
            
            if not service_info:
                return self.create_error_result("无法解析查询目标")
            
            # 调用MCP服务
            service_name = service_info['service']
            query_params = service_info['params']
            
            result_data = self.tool_manager.query_data(service_name, query_params)
            
            result = self.create_success_result(
                data=result_data,
                message=f"数据查询完成: {service_name}"
            )
            
            self.log_execution(goal, result)
            return result
            
        except Exception as e:
            error_message = f"数据查询失败: {str(e)}"
            self.logger.error(error_message)
            return self.create_error_result(error_message)
    
    def _parse_query_goal(self, goal: str, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """解析查询目标"""
        # 简化实现：根据关键词匹配服务
        goal_lower = goal.lower()
        
        # 可以根据实际需要扩展
        if 'database' in goal_lower or 'db' in goal_lower:
            return {
                'service': 'database_service',
                'params': {
                    'query': goal,
                    'context': context
                }
            }
        elif 'api' in goal_lower:
            return {
                'service': 'api_service', 
                'params': {
                    'endpoint': goal,
                    'context': context
                }
            }
        else:
            # 默认服务
            return {
                'service': 'example_service',
                'params': {
                    'action': 'query',
                    'query': goal,
                    'context': context
                }
            }


class NotificationAgent(BaseAgent):
    """通知Agent"""
    
    def __init__(self, tool_manager, llm_manager):
        super().__init__("NotificationAgent", tool_manager, llm_manager)
    
    def execute(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行通知任务"""
        try:
            if not self.validate_goal(goal):
                return self.create_error_result("通知目标无效")
            
            self.logger.info(f"执行通知任务: {goal}")
            
            # 解析通知目标
            notification_info = self._parse_notification_goal(goal, context)
            
            if not notification_info:
                return self.create_error_result("无法解析通知目标")
            
            # 发送通知
            service_name = notification_info['service']
            notification_params = notification_info['params']
            
            result_data = self.tool_manager.send_notification(service_name, notification_params)
            
            result = self.create_success_result(
                data=result_data,
                message=f"通知发送完成: {service_name}"
            )
            
            self.log_execution(goal, result)
            return result
            
        except Exception as e:
            error_message = f"通知发送失败: {str(e)}"
            self.logger.error(error_message)
            return self.create_error_result(error_message)
    
    def _parse_notification_goal(self, goal: str, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """解析通知目标"""
        goal_lower = goal.lower()
        
        if 'email' in goal_lower or '邮件' in goal_lower:
            return {
                'service': 'email_service',
                'params': {
                    'type': 'email',
                    'message': goal,
                    'context': context
                }
            }
        elif 'slack' in goal_lower:
            return {
                'service': 'slack_service',
                'params': {
                    'type': 'slack',
                    'message': goal,
                    'context': context
                }
            }
        else:
            return {
                'service': 'notification_service',
                'params': {
                    'type': 'general',
                    'message': goal,
                    'context': context
                }
            }


class ActionAgent(BaseAgent):
    """动作执行Agent"""
    
    def __init__(self, tool_manager, llm_manager):
        super().__init__("ActionAgent", tool_manager, llm_manager)
    
    def execute(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行动作任务"""
        try:
            if not self.validate_goal(goal):
                return self.create_error_result("动作目标无效")
            
            self.logger.info(f"执行动作任务: {goal}")
            
            # 解析动作目标
            action_info = self._parse_action_goal(goal, context)
            
            if not action_info:
                return self.create_error_result("无法解析动作目标")
            
            # 执行动作
            service_name = action_info['service']
            action_params = action_info['params']
            
            result_data = self.tool_manager.execute_action(service_name, action_params)
            
            result = self.create_success_result(
                data=result_data,
                message=f"动作执行完成: {service_name}"
            )
            
            self.log_execution(goal, result)
            return result
            
        except Exception as e:
            error_message = f"动作执行失败: {str(e)}"
            self.logger.error(error_message)
            return self.create_error_result(error_message)
    
    def _parse_action_goal(self, goal: str, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """解析动作目标"""
        return {
            'service': 'action_service',
            'params': {
                'action': goal,
                'context': context
            }
        }


class ReportAgent(BaseAgent):
    """报告Agent"""
    
    def __init__(self, tool_manager, llm_manager):
        super().__init__("ReportAgent", tool_manager, llm_manager)
    
    def execute(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行报告生成任务"""
        try:
            if not self.validate_goal(goal):
                return self.create_error_result("报告目标无效")
            
            self.logger.info(f"生成报告: {goal}")
            
            # 使用LLM生成报告总结
            mission_data = context.get('mission_data', {}) if context else {}
            summary = self.llm_manager.generate_summary(mission_data)
            
            result = self.create_success_result(
                data={'summary': summary},
                message="报告生成完成"
            )
            
            self.log_execution(goal, result)
            return result
            
        except Exception as e:
            error_message = f"报告生成失败: {str(e)}"
            self.logger.error(error_message)
            return self.create_error_result(error_message)


class ValidationAgent(BaseAgent):
    """验证Agent"""
    
    def __init__(self, tool_manager, llm_manager):
        super().__init__("ValidationAgent", tool_manager, llm_manager)
    
    def execute(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行验证任务"""
        try:
            if not self.validate_goal(goal):
                return self.create_error_result("验证目标无效")
            
            self.logger.info(f"执行验证: {goal}")
            
            # 简单的验证逻辑
            validation_result = self._perform_validation(goal, context)
            
            result = self.create_success_result(
                data=validation_result,
                message="验证完成"
            )
            
            self.log_execution(goal, result)
            return result
            
        except Exception as e:
            error_message = f"验证失败: {str(e)}"
            self.logger.error(error_message)
            return self.create_error_result(error_message)
    
    def _perform_validation(self, goal: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """执行验证逻辑"""
        # 简化实现，实际可以根据需要扩展
        return {
            'validated': True,
            'validation_result': f"验证通过: {goal}",
            'details': context
        }