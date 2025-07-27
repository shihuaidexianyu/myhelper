"""
核心数据结构定义
"""

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


class MissionStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 待处理
    PLANNING = "planning"        # 规划中
    EXECUTING = "executing"      # 执行中
    REPORTING = "reporting"      # 报告中
    RENDERING = "rendering"      # 渲染中
    NOTIFYING = "notifying"      # 通知中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 已失败


class SubtaskStatus(Enum):
    """子任务状态枚举"""
    PENDING = "pending"          # 待处理
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 失败
    SKIPPED = "skipped"         # 跳过


@dataclass
class Subtask:
    """子任务数据结构"""
    subtask_id: str
    subagent_name: str
    goal: str
    dependencies: List[str]
    status: SubtaskStatus = SubtaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Subtask':
        """从字典创建实例"""
        data = data.copy()
        if isinstance(data.get('status'), str):
            data['status'] = SubtaskStatus(data['status'])
        return cls(**data)


@dataclass
class ReportConfig:
    """报告配置"""
    style: Optional[str] = None  # CSS样式文件名
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportConfig':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class NotificationConfig:
    """通知配置"""
    type: str                    # 通知类型: email, slack, webhook等
    target: str                  # 通知目标: 邮箱地址、Slack频道等
    subject: Optional[str] = None # 通知主题
    extra_params: Optional[Dict[str, Any]] = None  # 额外参数
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationConfig':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class Mission:
    """任务实体 - 系统的核心数据结构"""
    mission_id: str
    natural_language_goal: str
    status: MissionStatus = MissionStatus.PENDING
    subtask_graph: List[Subtask] = None
    report_config: Optional[ReportConfig] = None
    notification_configs: List[NotificationConfig] = None
    result_page_url: Optional[str] = None
    final_summary: Optional[str] = None
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.subtask_graph is None:
            self.subtask_graph = []
        if self.notification_configs is None:
            self.notification_configs = []
    
    @classmethod
    def create_new(cls, natural_language_goal: str, 
                   report_config: Optional[ReportConfig] = None,
                   notification_configs: Optional[List[NotificationConfig]] = None) -> 'Mission':
        """创建新任务"""
        mission_id = str(uuid.uuid4())
        return cls(
            mission_id=mission_id,
            natural_language_goal=natural_language_goal,
            report_config=report_config,
            notification_configs=notification_configs or []
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        data['subtask_graph'] = [subtask.to_dict() for subtask in self.subtask_graph]
        if self.report_config:
            data['report_config'] = self.report_config.to_dict()
        data['notification_configs'] = [config.to_dict() for config in self.notification_configs]
        return data
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Mission':
        """从字典创建实例"""
        data = data.copy()
        
        # 转换状态枚举
        if isinstance(data.get('status'), str):
            data['status'] = MissionStatus(data['status'])
        
        # 转换子任务图
        if 'subtask_graph' in data and data['subtask_graph']:
            data['subtask_graph'] = [Subtask.from_dict(subtask) for subtask in data['subtask_graph']]
        
        # 转换报告配置
        if 'report_config' in data and data['report_config']:
            data['report_config'] = ReportConfig.from_dict(data['report_config'])
        
        # 转换通知配置
        if 'notification_configs' in data and data['notification_configs']:
            data['notification_configs'] = [
                NotificationConfig.from_dict(config) for config in data['notification_configs']
            ]
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Mission':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_pending_subtasks(self) -> List[Subtask]:
        """获取待处理的子任务"""
        return [task for task in self.subtask_graph if task.status == SubtaskStatus.PENDING]
    
    def get_ready_subtasks(self) -> List[Subtask]:
        """获取依赖已完成、可以执行的子任务"""
        completed_tasks = {task.subtask_id for task in self.subtask_graph 
                          if task.status == SubtaskStatus.COMPLETED}
        
        ready_tasks = []
        for task in self.get_pending_subtasks():
            if all(dep in completed_tasks for dep in task.dependencies):
                ready_tasks.append(task)
        
        return ready_tasks
    
    def is_all_subtasks_completed(self) -> bool:
        """检查是否所有子任务都已完成"""
        if not self.subtask_graph:
            return True
        return all(task.status in [SubtaskStatus.COMPLETED, SubtaskStatus.SKIPPED] 
                  for task in self.subtask_graph)
    
    def has_failed_subtasks(self) -> bool:
        """检查是否有失败的子任务"""
        return any(task.status == SubtaskStatus.FAILED for task in self.subtask_graph)
    
    def update_status(self, new_status: MissionStatus, error_message: Optional[str] = None):
        """更新任务状态"""
        self.status = new_status
        if error_message:
            self.error_message = error_message
        
        if new_status == MissionStatus.EXECUTING and self.started_at is None:
            self.started_at = datetime.now().isoformat()
        elif new_status in [MissionStatus.COMPLETED, MissionStatus.FAILED]:
            self.completed_at = datetime.now().isoformat()
    
    def add_subtask(self, subagent_name: str, goal: str, dependencies: List[str] = None) -> str:
        """添加子任务"""
        subtask_id = f"task_{len(self.subtask_graph) + 1}"
        subtask = Subtask(
            subtask_id=subtask_id,
            subagent_name=subagent_name,
            goal=goal,
            dependencies=dependencies or []
        )
        self.subtask_graph.append(subtask)
        return subtask_id
    
    def update_subtask_status(self, subtask_id: str, status: SubtaskStatus, 
                             result: Optional[Dict[str, Any]] = None,
                             error_message: Optional[str] = None):
        """更新子任务状态"""
        for task in self.subtask_graph:
            if task.subtask_id == subtask_id:
                task.status = status
                if result is not None:
                    task.result = result
                if error_message:
                    task.error_message = error_message
                
                if status == SubtaskStatus.IN_PROGRESS and task.started_at is None:
                    task.started_at = datetime.now().isoformat()
                elif status in [SubtaskStatus.COMPLETED, SubtaskStatus.FAILED, SubtaskStatus.SKIPPED]:
                    task.completed_at = datetime.now().isoformat()
                break