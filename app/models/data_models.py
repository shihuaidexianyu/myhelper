"""
数据模型定义
定义系统中使用的数据结构
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    """任务状态枚举"""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ToolType(Enum):
    """工具类型枚举"""
    SHELL_COMMAND = "shell_command"
    HTTP_REQUEST = "http_request"
    PYTHON_FUNCTION = "python_function"


class ParameterType(Enum):
    """参数类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: ParameterType
    description: str
    required: bool = False
    default: Any = None


@dataclass
class Tool:
    """工具定义"""
    id: str
    name: str
    type: ToolType
    description: str
    parameters: List[ToolParameter]
    command: Optional[str] = None  # 用于shell_command类型
    url: Optional[str] = None      # 用于http_request类型
    function: Optional[str] = None # 用于python_function类型
    timeout: int = 30
    retry_count: int = 0


@dataclass
class Task:
    """任务定义"""
    id: str
    name: str
    description: str
    authorized_tool_ids: List[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class MCPRequest:
    """MyHelper控制协议请求"""
    protocol: str = "MCP"
    version: str = "1.0"
    tool_name: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None


@dataclass
class MCPResponse:
    """MyHelper控制协议响应"""
    status: str  # success, failed
    output: Optional[str] = None
    error: Optional[str] = None
    request_id: Optional[str] = None
    execution_time: Optional[float] = None


@dataclass
class PlanStep:
    """计划步骤"""
    step_id: str
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    retry_on_failure: bool = False
    critical: bool = True  # 如果失败是否应该中止整个任务


@dataclass
class Plan:
    """执行计划"""
    plan_id: str
    task_id: str
    steps: List[PlanStep]
    created_at: str
    reasoning: Optional[str] = None


@dataclass
class ExecutionStepResult:
    """执行步骤结果"""
    step_id: str
    status: str  # success, failed, skipped
    started_at: str
    finished_at: str
    mcp_request: MCPRequest
    mcp_response: MCPResponse
    error_message: Optional[str] = None


@dataclass
class ExecutionLog:
    """执行日志"""
    execution_id: str
    plan_id: str
    status: str  # running, success, failed
    started_at: str
    finished_at: Optional[str]
    step_results: List[ExecutionStepResult] = field(default_factory=list)
    final_message: Optional[str] = None


@dataclass
class Report:
    """任务报告"""
    report_id: str
    task_id: str
    status: TaskStatus
    trigger_context: Dict[str, Any]
    timestamps: Dict[str, Optional[str]]
    plan: Optional[Plan] = None
    execution_log: Optional[ExecutionLog] = None
    final_summary: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


@dataclass
class Learning:
    """学习经验"""
    learning_id: str
    task_id: str
    category: str  # success_pattern, failure_analysis, optimization
    title: str
    description: str
    context: Dict[str, Any]
    created_at: str
    confidence_score: float = 0.5  # 0-1之间的置信度分数


@dataclass
class Timestamps:
    """时间戳集合"""
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    
    @classmethod
    def now(cls) -> str:
        """获取当前UTC时间戳"""
        return datetime.utcnow().isoformat()


def validate_mcp_request(request: MCPRequest, tool: Tool) -> List[str]:
    """验证MCP请求是否符合工具定义
    
    Returns:
        List[str]: 验证错误列表，空列表表示验证通过
    """
    errors = []
    
    # 验证协议版本
    if request.protocol != "MCP":
        errors.append(f"Invalid protocol: {request.protocol}, expected 'MCP'")
    
    if request.version != "1.0":
        errors.append(f"Unsupported version: {request.version}, expected '1.0'")
    
    # 验证工具名称
    if request.tool_name != tool.id:
        errors.append(f"Tool name mismatch: {request.tool_name} != {tool.id}")
    
    # 验证参数
    required_params = {p.name for p in tool.parameters if p.required}
    provided_params = set(request.params.keys())
    
    # 检查缺失的必需参数
    missing_params = required_params - provided_params
    if missing_params:
        errors.append(f"Missing required parameters: {missing_params}")
    
    # 检查参数类型
    for param in tool.parameters:
        if param.name in request.params:
            value = request.params[param.name]
            if not _validate_parameter_type(value, param.type):
                errors.append(f"Parameter '{param.name}' has invalid type")
    
    return errors


def _validate_parameter_type(value: Any, param_type: ParameterType) -> bool:
    """验证参数值类型"""
    if param_type == ParameterType.STRING:
        return isinstance(value, str)
    elif param_type == ParameterType.INTEGER:
        return isinstance(value, int)
    elif param_type == ParameterType.BOOLEAN:
        return isinstance(value, bool)
    elif param_type == ParameterType.ARRAY:
        return isinstance(value, list)
    elif param_type == ParameterType.OBJECT:
        return isinstance(value, dict)
    return False