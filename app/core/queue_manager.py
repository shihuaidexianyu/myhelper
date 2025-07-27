"""
队列管理器 - 基于文件系统的持久化任务队列
"""

import os
import threading
from pathlib import Path
from typing import Optional, List
import logging
import time
import fcntl

logger = logging.getLogger(__name__)


class QueueManager:
    """队列管理器 - 持久化任务队列的"调度员"""
    
    def __init__(self, queue_dir: str = "data/queue"):
        self.queue_dir = Path(queue_dir)
        self.lock = threading.RLock()
        
        # 队列子目录
        self.pending_dir = self.queue_dir / "pending"      # 待处理队列
        self.processing_dir = self.queue_dir / "processing" # 处理中队列
        self.completed_dir = self.queue_dir / "completed"   # 已完成队列
        self.failed_dir = self.queue_dir / "failed"         # 失败队列
        
        # 创建队列目录
        for directory in [self.pending_dir, self.processing_dir, 
                         self.completed_dir, self.failed_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info("QueueManager初始化完成")
    
    def _get_queue_file_path(self, mission_id: str, queue_type: str) -> Path:
        """获取队列文件路径"""
        queue_dirs = {
            'pending': self.pending_dir,
            'processing': self.processing_dir,
            'completed': self.completed_dir,
            'failed': self.failed_dir
        }
        
        if queue_type not in queue_dirs:
            raise ValueError(f"无效的队列类型: {queue_type}")
        
        return queue_dirs[queue_type] / f"{mission_id}.queue"
    
    def _write_queue_file(self, file_path: Path, mission_id: str, 
                         metadata: Optional[dict] = None) -> bool:
        """写入队列文件"""
        try:
            import json
            from datetime import datetime
            
            data = {
                'mission_id': mission_id,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            # 原子性写入
            temp_file = file_path.with_suffix('.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                # 获取排他锁
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # 原子性重命名
            temp_file.rename(file_path)
            return True
            
        except Exception as e:
            logger.error(f"写入队列文件失败 {file_path}: {e}")
            return False
    
    def _move_queue_file(self, mission_id: str, from_queue: str, to_queue: str) -> bool:
        """在队列间移动文件"""
        try:
            from_path = self._get_queue_file_path(mission_id, from_queue)
            to_path = self._get_queue_file_path(mission_id, to_queue)
            
            if not from_path.exists():
                logger.warning(f"源队列文件不存在: {from_path}")
                return False
            
            # 原子性移动
            from_path.rename(to_path)
            return True
            
        except Exception as e:
            logger.error(f"移动队列文件失败 {mission_id} from {from_queue} to {to_queue}: {e}")
            return False
    
    def enqueue(self, mission_id: str, metadata: Optional[dict] = None) -> bool:
        """将任务加入待处理队列"""
        with self.lock:
            file_path = self._get_queue_file_path(mission_id, 'pending')
            
            if file_path.exists():
                logger.warning(f"任务已在队列中: {mission_id}")
                return False
            
            success = self._write_queue_file(file_path, mission_id, metadata)
            if success:
                logger.info(f"任务入队: {mission_id}")
            
            return success
    
    def dequeue(self) -> Optional[str]:
        """从待处理队列取出下一个任务"""
        with self.lock:
            # 获取最早的任务文件
            queue_files = list(self.pending_dir.glob("*.queue"))
            
            if not queue_files:
                return None
            
            # 按文件修改时间排序，取最早的
            queue_files.sort(key=lambda f: f.stat().st_mtime)
            earliest_file = queue_files[0]
            
            # 获取任务ID
            mission_id = earliest_file.stem
            
            # 移动到处理中队列
            if self._move_queue_file(mission_id, 'pending', 'processing'):
                logger.info(f"任务出队: {mission_id}")
                return mission_id
            
            return None
    
    def mark_processing(self, mission_id: str) -> bool:
        """标记任务为处理中"""
        with self.lock:
            return self._move_queue_file(mission_id, 'pending', 'processing')
    
    def mark_completed(self, mission_id: str) -> bool:
        """标记任务为已完成"""
        with self.lock:
            success = self._move_queue_file(mission_id, 'processing', 'completed')
            if success:
                logger.info(f"任务完成: {mission_id}")
            return success
    
    def mark_failed(self, mission_id: str, error_info: Optional[dict] = None) -> bool:
        """标记任务为失败"""
        with self.lock:
            # 先移动文件
            success = self._move_queue_file(mission_id, 'processing', 'failed')
            
            if success and error_info:
                # 更新失败信息
                file_path = self._get_queue_file_path(mission_id, 'failed')
                try:
                    import json
                    with open(file_path, 'r+', encoding='utf-8') as f:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                        try:
                            data = json.load(f)
                            data['error_info'] = error_info
                            f.seek(0)
                            json.dump(data, f, ensure_ascii=False)
                            f.truncate()
                        finally:
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except Exception as e:
                    logger.error(f"更新失败信息时出错 {mission_id}: {e}")
            
            if success:
                logger.info(f"任务失败: {mission_id}")
            
            return success
    
    def retry_failed_task(self, mission_id: str) -> bool:
        """重试失败的任务"""
        with self.lock:
            return self._move_queue_file(mission_id, 'failed', 'pending')
    
    def get_queue_size(self, queue_type: str) -> int:
        """获取指定队列的大小"""
        queue_dirs = {
            'pending': self.pending_dir,
            'processing': self.processing_dir,
            'completed': self.completed_dir,
            'failed': self.failed_dir
        }
        
        if queue_type not in queue_dirs:
            return 0
        
        return len(list(queue_dirs[queue_type].glob("*.queue")))
    
    def get_queue_status(self) -> dict:
        """获取所有队列的状态"""
        return {
            'pending': self.get_queue_size('pending'),
            'processing': self.get_queue_size('processing'),
            'completed': self.get_queue_size('completed'),
            'failed': self.get_queue_size('failed')
        }
    
    def list_queue_tasks(self, queue_type: str, limit: Optional[int] = None) -> List[dict]:
        """列出指定队列中的任务"""
        queue_dirs = {
            'pending': self.pending_dir,
            'processing': self.processing_dir,
            'completed': self.completed_dir,
            'failed': self.failed_dir
        }
        
        if queue_type not in queue_dirs:
            return []
        
        tasks = []
        queue_files = list(queue_dirs[queue_type].glob("*.queue"))
        
        # 按文件修改时间排序
        queue_files.sort(key=lambda f: f.stat().st_mtime)
        
        if limit:
            queue_files = queue_files[:limit]
        
        for queue_file in queue_files:
            try:
                import json
                with open(queue_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    tasks.append(data)
            except Exception as e:
                logger.warning(f"读取队列文件失败 {queue_file}: {e}")
        
        return tasks
    
    def cleanup_completed_tasks(self, max_keep: int = 100) -> int:
        """清理已完成的任务（保留最近的max_keep个）"""
        completed_files = list(self.completed_dir.glob("*.queue"))
        
        if len(completed_files) <= max_keep:
            return 0
        
        # 按文件修改时间排序，删除最旧的
        completed_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        files_to_delete = completed_files[max_keep:]
        
        deleted_count = 0
        for file_path in files_to_delete:
            try:
                file_path.unlink()
                deleted_count += 1
            except Exception as e:
                logger.error(f"删除队列文件失败 {file_path}: {e}")
        
        logger.info(f"清理了 {deleted_count} 个已完成的队列文件")
        return deleted_count
    
    def get_processing_tasks(self) -> List[str]:
        """获取正在处理的任务ID列表"""
        return [f.stem for f in self.processing_dir.glob("*.queue")]
    
    def get_pending_tasks(self) -> List[str]:
        """获取待处理的任务ID列表"""
        files = list(self.pending_dir.glob("*.queue"))
        # 按文件修改时间排序
        files.sort(key=lambda f: f.stat().st_mtime)
        return [f.stem for f in files]
    
    def has_pending_tasks(self) -> bool:
        """检查是否有待处理的任务"""
        return self.get_queue_size('pending') > 0
    
    def remove_from_queue(self, mission_id: str, queue_type: str) -> bool:
        """从指定队列中移除任务"""
        try:
            file_path = self._get_queue_file_path(mission_id, queue_type)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"从{queue_type}队列移除任务: {mission_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"从队列移除任务失败 {mission_id}: {e}")
            return False
    
    def recover_orphaned_tasks(self) -> int:
        """恢复孤儿任务（处理中但实际没有在处理的任务）"""
        recovered_count = 0
        processing_files = list(self.processing_dir.glob("*.queue"))
        
        for file_path in processing_files:
            try:
                import json
                from datetime import datetime, timedelta
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 检查任务是否长时间处于处理状态
                timestamp_str = data.get('timestamp')
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if datetime.now() - timestamp > timedelta(hours=1):  # 超过1小时
                        mission_id = file_path.stem
                        if self._move_queue_file(mission_id, 'processing', 'pending'):
                            recovered_count += 1
                            logger.info(f"恢复孤儿任务: {mission_id}")
                
            except Exception as e:
                logger.error(f"恢复孤儿任务时出错 {file_path}: {e}")
        
        if recovered_count > 0:
            logger.info(f"恢复了 {recovered_count} 个孤儿任务")
        
        return recovered_count