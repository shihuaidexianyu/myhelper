"""
文件处理工具
"""
import json
import os
import shutil
from typing import Dict, Any, Optional
import tempfile


def safe_write_json(file_path: str, data: Dict[str, Any], indent: int = 2) -> bool:
    """安全地写入JSON文件（原子操作）"""
    try:
        # 使用临时文件确保原子性写入
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        
        with tempfile.NamedTemporaryFile(
            mode='w', 
            dir=dir_name, 
            delete=False, 
            suffix='.tmp',
            encoding='utf-8'
        ) as temp_file:
            json.dump(data, temp_file, ensure_ascii=False, indent=indent)
            temp_file_path = temp_file.name
        
        # 原子性重命名
        shutil.move(temp_file_path, file_path)
        return True
        
    except Exception as e:
        # 清理临时文件
        try:
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        except:
            pass
        return False


def safe_read_json(file_path: str) -> Optional[Dict[str, Any]]:
    """安全地读取JSON文件"""
    try:
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def ensure_directory(dir_path: str) -> bool:
    """确保目录存在"""
    try:
        os.makedirs(dir_path, exist_ok=True)
        return True
    except OSError:
        return False


def get_file_size(file_path: str) -> Optional[int]:
    """获取文件大小（字节）"""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return None


def cleanup_old_files(directory: str, max_age_days: int = 30) -> int:
    """清理旧文件，返回删除的文件数量"""
    if not os.path.exists(directory):
        return 0
    
    import time
    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 3600
    deleted_count = 0
    
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    try:
                        os.unlink(file_path)
                        deleted_count += 1
                    except OSError:
                        continue
    except OSError:
        pass
    
    return deleted_count