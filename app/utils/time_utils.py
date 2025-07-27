"""
时间处理工具
"""
from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """获取当前UTC时间"""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """获取当前UTC时间的ISO格式字符串"""
    return utc_now().isoformat()


def parse_iso_datetime(iso_string: str) -> Optional[datetime]:
    """解析ISO格式时间字符串"""
    try:
        # 处理不同的ISO格式
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1] + '+00:00'
        return datetime.fromisoformat(iso_string)
    except (ValueError, TypeError):
        return None


def format_duration(seconds: float) -> str:
    """格式化时长显示"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def calculate_duration(start_time: str, end_time: str) -> Optional[float]:
    """计算两个ISO时间字符串之间的时长（秒）"""
    start_dt = parse_iso_datetime(start_time)
    end_dt = parse_iso_datetime(end_time)
    
    if start_dt and end_dt:
        return (end_dt - start_dt).total_seconds()
    return None