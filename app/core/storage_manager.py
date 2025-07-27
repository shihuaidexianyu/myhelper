"""
数据存储管理器
负责所有对data/目录中JSON文件的读写操作，并处理并发安全问题
"""
import json
import os
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging


class StorageManager:
    """线程安全的数据存储管理器"""
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = data_dir
        self._ensure_data_dir()
        
        # 为不同的数据文件使用不同的锁，提高并发性能
        self._tasks_lock = threading.RLock()
        self._tools_lock = threading.RLock()
        self._reports_lock = threading.RLock()
        self._learnings_lock = threading.RLock()
        
        self.logger = logging.getLogger(__name__)
    
    def _ensure_data_dir(self):
        """确保数据目录结构存在"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, 'reports'), exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, 'learnings'), exist_ok=True)
        
        # 创建默认文件如果不存在
        tasks_file = os.path.join(self.data_dir, 'tasks.json')
        tools_file = os.path.join(self.data_dir, 'tools.json')
        
        if not os.path.exists(tasks_file):
            with open(tasks_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(tools_file):
            with open(tools_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    def _read_json_file(self, file_path: str, lock: threading.RLock) -> Dict:
        """线程安全地读取JSON文件"""
        with lock:
            try:
                if not os.path.exists(file_path):
                    return {}
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"Error reading {file_path}: {e}")
                return {}
    
    def _write_json_file(self, file_path: str, data: Dict, lock: threading.RLock):
        """线程安全地写入JSON文件"""
        with lock:
            try:
                # 使用临时文件确保原子性写入
                temp_path = file_path + '.tmp'
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # 原子性重命名
                os.replace(temp_path, file_path)
            except IOError as e:
                self.logger.error(f"Error writing {file_path}: {e}")
                raise
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """从tasks.json读取任务定义"""
        tasks_file = os.path.join(self.data_dir, 'tasks.json')
        tasks = self._read_json_file(tasks_file, self._tasks_lock)
        return tasks.get(task_id)
    
    def get_tool(self, tool_name: str) -> Optional[Dict]:
        """从tools.json读取工具定义"""
        tools_file = os.path.join(self.data_dir, 'tools.json')
        tools = self._read_json_file(tools_file, self._tools_lock)
        return tools.get(tool_name)
    
    def get_authorized_tools(self, tool_ids: List[str]) -> Dict[str, Dict]:
        """根据任务授权的ID列表，获取完整的工具定义列表"""
        tools_file = os.path.join(self.data_dir, 'tools.json')
        all_tools = self._read_json_file(tools_file, self._tools_lock)
        
        authorized_tools = {}
        for tool_id in tool_ids:
            if tool_id in all_tools:
                authorized_tools[tool_id] = all_tools[tool_id]
            else:
                self.logger.warning(f"Tool {tool_id} not found in tools.json")
        
        return authorized_tools
    
    def create_report(self, task_id: str, trigger_context: Dict) -> str:
        """在data/reports/目录中创建一个新的报告文件"""
        report_id = str(uuid.uuid4())
        report_data = {
            "report_id": report_id,
            "task_id": task_id,
            "status": "queued",
            "trigger_context": trigger_context,
            "timestamps": {
                "created_at": datetime.utcnow().isoformat(),
                "started_at": None,
                "finished_at": None
            },
            "plan": None,
            "execution_log": None,
            "final_summary": None,
            "error_details": None
        }
        
        report_file = os.path.join(self.data_dir, 'reports', f'{report_id}.json')
        self._write_json_file(report_file, report_data, self._reports_lock)
        
        self.logger.info(f"Created new report: {report_id} for task: {task_id}")
        return report_id
    
    def update_report(self, report_id: str, update_data: Dict):
        """更新指定报告文件的内容"""
        report_file = os.path.join(self.data_dir, 'reports', f'{report_id}.json')
        
        with self._reports_lock:
            # 读取现有数据
            existing_data = self._read_json_file(report_file, threading.RLock())
            if not existing_data:
                raise FileNotFoundError(f"Report {report_id} not found")
            
            # 更新数据
            existing_data.update(update_data)
            
            # 自动更新时间戳
            if 'status' in update_data:
                if update_data['status'] == 'running' and not existing_data['timestamps']['started_at']:
                    existing_data['timestamps']['started_at'] = datetime.utcnow().isoformat()
                elif update_data['status'] in ['success', 'failed']:
                    existing_data['timestamps']['finished_at'] = datetime.utcnow().isoformat()
            
            # 写回文件
            self._write_json_file(report_file, existing_data, threading.RLock())
    
    def get_report(self, report_id: str) -> Optional[Dict]:
        """读取并返回指定报告的内容"""
        report_file = os.path.join(self.data_dir, 'reports', f'{report_id}.json')
        return self._read_json_file(report_file, self._reports_lock)
    
    def save_learning(self, learning_data: Dict):
        """将新的学习经验保存到data/learnings/"""
        learning_id = str(uuid.uuid4())
        learning_data['learning_id'] = learning_id
        learning_data['created_at'] = datetime.utcnow().isoformat()
        
        learning_file = os.path.join(self.data_dir, 'learnings', f'{learning_id}.json')
        self._write_json_file(learning_file, learning_data, self._learnings_lock)
        
        self.logger.info(f"Saved new learning: {learning_id}")
        return learning_id
    
    def get_learnings(self, limit: int = 10) -> List[Dict]:
        """获取最近的学习经验"""
        learnings_dir = os.path.join(self.data_dir, 'learnings')
        learnings = []
        
        with self._learnings_lock:
            if not os.path.exists(learnings_dir):
                return learnings
            
            # 获取所有学习文件，按修改时间排序
            files = []
            for filename in os.listdir(learnings_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(learnings_dir, filename)
                    files.append((file_path, os.path.getmtime(file_path)))
            
            # 按时间降序排序，获取最新的
            files.sort(key=lambda x: x[1], reverse=True)
            
            for file_path, _ in files[:limit]:
                learning = self._read_json_file(file_path, threading.RLock())
                if learning:
                    learnings.append(learning)
        
        return learnings
    
    def create_task(self, name: str, description: str, goal: str, authorized_tool_ids: List[str] = None) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        task_data = {
            'name': name,
            'description': description,
            'goal': goal,
            'authorized_tool_ids': authorized_tool_ids or [],
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        tasks_file = os.path.join(self.data_dir, 'tasks.json')
        with self._tasks_lock:
            tasks = self._read_json_file(tasks_file, threading.RLock())
            tasks[task_id] = task_data
            self._write_json_file(tasks_file, tasks, threading.RLock())
        
        self.logger.info(f"Created new task: {task_id}")
        return task_id
    
    def update_task(self, task_id: str, update_data: Dict):
        """更新任务"""
        tasks_file = os.path.join(self.data_dir, 'tasks.json')
        with self._tasks_lock:
            tasks = self._read_json_file(tasks_file, threading.RLock())
            if task_id not in tasks:
                raise KeyError(f"Task {task_id} not found")
            
            tasks[task_id].update(update_data)
            tasks[task_id]['updated_at'] = datetime.utcnow().isoformat()
            self._write_json_file(tasks_file, tasks, threading.RLock())
        
        self.logger.info(f"Updated task: {task_id}")
    
    def delete_task(self, task_id: str):
        """删除任务"""
        tasks_file = os.path.join(self.data_dir, 'tasks.json')
        with self._tasks_lock:
            tasks = self._read_json_file(tasks_file, threading.RLock())
            if task_id not in tasks:
                raise KeyError(f"Task {task_id} not found")
            
            del tasks[task_id]
            self._write_json_file(tasks_file, tasks, threading.RLock())
        
        self.logger.info(f"Deleted task: {task_id}")
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取单个任务"""
        tasks_file = os.path.join(self.data_dir, 'tasks.json')
        with self._tasks_lock:
            tasks = self._read_json_file(tasks_file, threading.RLock())
            return tasks.get(task_id)