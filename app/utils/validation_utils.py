"""
验证工具
"""
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """验证URL格式"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def validate_task_id(task_id: str) -> bool:
    """验证任务ID格式"""
    # 任务ID应该是字母、数字、下划线、连字符的组合
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, task_id)) and len(task_id) <= 50


def validate_tool_name(tool_name: str) -> bool:
    """验证工具名称格式"""
    # 工具名称应该是字母、数字、下划线的组合
    pattern = r'^[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, tool_name)) and len(tool_name) <= 50


def validate_json_structure(data: Any, required_fields: List[str]) -> List[str]:
    """验证JSON结构，返回缺失字段列表"""
    if not isinstance(data, dict):
        return ["Root object must be a dictionary"]
    
    missing_fields = []
    for field in required_fields:
        if field not in data:
            missing_fields.append(f"Missing required field: {field}")
    
    return missing_fields


def validate_trigger_context(context: Dict[str, Any]) -> List[str]:
    """验证触发上下文"""
    errors = []
    
    if not isinstance(context, dict):
        errors.append("Trigger context must be a dictionary")
        return errors
    
    # 检查常见字段的格式
    if 'branch' in context and not isinstance(context['branch'], str):
        errors.append("Branch must be a string")
    
    if 'commit_hash' in context:
        commit_hash = context['commit_hash']
        if not isinstance(commit_hash, str) or len(commit_hash) not in [7, 40]:
            errors.append("Commit hash must be a 7 or 40 character string")
    
    if 'environment' in context:
        environment = context['environment']
        if not isinstance(environment, str) or environment not in ['development', 'staging', 'production']:
            errors.append("Environment must be one of: development, staging, production")
    
    return errors


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除不安全字符"""
    # 移除路径分隔符和其他不安全字符
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 移除控制字符
    sanitized = re.sub(r'[\x00-\x1f\x7f]', '', sanitized)
    # 限制长度
    return sanitized[:255]


def validate_port(port: Any) -> bool:
    """验证端口号"""
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except (ValueError, TypeError):
        return False