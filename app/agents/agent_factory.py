"""
Agent工厂 - 负责创建和管理Agent实例
"""

import logging
from typing import Dict, Optional
from .base_agent import (
    BaseAgent, OrchestratorAgent, DataQueryAgent, 
    NotificationAgent, ActionAgent, ReportAgent, ValidationAgent
)

logger = logging.getLogger(__name__)


class AgentFactory:
    """Agent工厂类"""
    
    def __init__(self, tool_manager, llm_manager):
        self.tool_manager = tool_manager
        self.llm_manager = llm_manager
        self._agent_registry = {}
        self._agent_instances = {}
        
        # 注册内置Agent
        self._register_builtin_agents()
    
    def _register_builtin_agents(self):
        """注册内置Agent类型"""
        self._agent_registry = {
            'OrchestratorAgent': OrchestratorAgent,
            'DataQueryAgent': DataQueryAgent,
            'NotificationAgent': NotificationAgent,
            'ActionAgent': ActionAgent,
            'ReportAgent': ReportAgent,
            'ValidationAgent': ValidationAgent
        }
    
    def create_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """创建Agent实例"""
        try:
            if agent_type not in self._agent_registry:
                logger.error(f"未知的Agent类型: {agent_type}")
                return None
            
            # 检查是否已有实例（单例模式）
            if agent_type in self._agent_instances:
                return self._agent_instances[agent_type]
            
            # 创建新实例
            agent_class = self._agent_registry[agent_type]
            agent_instance = agent_class(self.tool_manager, self.llm_manager)
            
            # 缓存实例
            self._agent_instances[agent_type] = agent_instance
            
            logger.info(f"创建Agent实例: {agent_type}")
            return agent_instance
            
        except Exception as e:
            logger.error(f"创建Agent失败 {agent_type}: {e}")
            return None
    
    def get_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """获取Agent实例（如果不存在则创建）"""
        return self.create_agent(agent_type)
    
    def get_available_agents(self) -> list:
        """获取可用的Agent类型列表"""
        return list(self._agent_registry.keys())
    
    def register_agent(self, agent_type: str, agent_class):
        """注册自定义Agent类型"""
        try:
            if not issubclass(agent_class, BaseAgent):
                raise ValueError(f"Agent类必须继承自BaseAgent: {agent_class}")
            
            self._agent_registry[agent_type] = agent_class
            logger.info(f"注册自定义Agent: {agent_type}")
            
        except Exception as e:
            logger.error(f"注册Agent失败 {agent_type}: {e}")
    
    def unregister_agent(self, agent_type: str):
        """注销Agent类型"""
        if agent_type in self._agent_registry:
            del self._agent_registry[agent_type]
            
            # 清理实例缓存
            if agent_type in self._agent_instances:
                del self._agent_instances[agent_type]
            
            logger.info(f"注销Agent: {agent_type}")
    
    def clear_agent_cache(self):
        """清理Agent实例缓存"""
        self._agent_instances.clear()
        logger.info("清理Agent实例缓存")
    
    def get_agent_info(self, agent_type: str) -> Optional[Dict]:
        """获取Agent信息"""
        if agent_type not in self._agent_registry:
            return None
        
        agent_class = self._agent_registry[agent_type]
        instance_exists = agent_type in self._agent_instances
        
        return {
            'type': agent_type,
            'class': agent_class.__name__,
            'module': agent_class.__module__,
            'doc': agent_class.__doc__,
            'instance_cached': instance_exists
        }
    
    def get_all_agents_info(self) -> Dict[str, Dict]:
        """获取所有Agent信息"""
        return {
            agent_type: self.get_agent_info(agent_type)
            for agent_type in self._agent_registry.keys()
        }