"""
任务管理器 - 负责任务数据的持久化存储和管理
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import fcntl
from datetime import datetime

from .models import Mission, MissionStatus

logger = logging.getLogger(__name__)


class MissionManager:
    """任务管理器 - 任务数据的"管家"""
    
    def __init__(self, missions_dir: str = "data/missions"):
        self.missions_dir = Path(missions_dir)
        self.lock = threading.RLock()
        
        # 确保任务目录存在
        self.missions_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建索引缓存
        self._index_cache = {}
        self._cache_lock = threading.RLock()
        
        # 重建索引
        self._rebuild_index()
    
    def _get_mission_file_path(self, mission_id: str) -> Path:
        """获取任务文件路径"""
        return self.missions_dir / f"{mission_id}.json"
    
    def _rebuild_index(self):
        """重建任务索引缓存"""
        with self._cache_lock:
            self._index_cache = {}
            
            for mission_file in self.missions_dir.glob("*.json"):
                try:
                    mission_id = mission_file.stem
                    with open(mission_file, 'r', encoding='utf-8') as f:
                        mission_data = json.load(f)
                    
                    self._index_cache[mission_id] = {
                        'status': mission_data.get('status', 'unknown'),
                        'created_at': mission_data.get('created_at'),
                        'natural_language_goal': mission_data.get('natural_language_goal', ''),
                        'file_path': str(mission_file)
                    }
                except Exception as e:
                    logger.warning(f"跳过无效的任务文件 {mission_file}: {e}")
        
        logger.info(f"重建任务索引完成，共 {len(self._index_cache)} 个任务")
    
    def create_mission(self, mission: Mission) -> bool:
        """创建新任务"""
        try:
            file_path = self._get_mission_file_path(mission.mission_id)
            
            # 检查任务是否已存在
            if file_path.exists():
                logger.warning(f"任务已存在: {mission.mission_id}")
                return False
            
            # 原子性写入
            temp_file = file_path.with_suffix('.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                # 获取文件锁
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(mission.to_json())
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # 原子性重命名
            temp_file.rename(file_path)
            
            # 更新索引缓存
            with self._cache_lock:
                self._index_cache[mission.mission_id] = {
                    'status': mission.status.value,
                    'created_at': mission.created_at,
                    'natural_language_goal': mission.natural_language_goal,
                    'file_path': str(file_path)
                }
            
            logger.info(f"任务创建成功: {mission.mission_id}")
            return True
            
        except Exception as e:
            logger.error(f"任务创建失败 {mission.mission_id}: {e}")
            return False
    
    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """获取任务"""
        try:
            file_path = self._get_mission_file_path(mission_id)
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                # 获取共享锁进行读取
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    mission_data = json.load(f)
                    return Mission.from_dict(mission_data)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    
        except Exception as e:
            logger.error(f"任务读取失败 {mission_id}: {e}")
            return None
    
    def update_mission(self, mission: Mission) -> bool:
        """更新任务"""
        try:
            file_path = self._get_mission_file_path(mission.mission_id)
            
            if not file_path.exists():
                logger.warning(f"任务不存在: {mission.mission_id}")
                return False
            
            # 原子性写入
            temp_file = file_path.with_suffix('.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                # 获取排他锁
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(mission.to_json())
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # 原子性重命名
            temp_file.rename(file_path)
            
            # 更新索引缓存
            with self._cache_lock:
                self._index_cache[mission.mission_id] = {
                    'status': mission.status.value,
                    'created_at': mission.created_at,
                    'natural_language_goal': mission.natural_language_goal,
                    'file_path': str(file_path)
                }
            
            logger.debug(f"任务更新成功: {mission.mission_id}")
            return True
            
        except Exception as e:
            logger.error(f"任务更新失败 {mission.mission_id}: {e}")
            return False
    
    def delete_mission(self, mission_id: str) -> bool:
        """删除任务"""
        try:
            file_path = self._get_mission_file_path(mission_id)
            
            if file_path.exists():
                file_path.unlink()
                
                # 从索引缓存中移除
                with self._cache_lock:
                    self._index_cache.pop(mission_id, None)
                
                logger.info(f"任务删除成功: {mission_id}")
                return True
            else:
                logger.warning(f"任务不存在: {mission_id}")
                return False
                
        except Exception as e:
            logger.error(f"任务删除失败 {mission_id}: {e}")
            return False
    
    def list_missions(self, status: Optional[MissionStatus] = None, 
                     limit: Optional[int] = None,
                     offset: int = 0) -> List[Dict[str, Any]]:
        """列出任务（返回基本信息，不包含完整数据）"""
        with self._cache_lock:
            missions = []
            
            for mission_id, info in self._index_cache.items():
                if status is None or info['status'] == status.value:
                    missions.append({
                        'mission_id': mission_id,
                        'status': info['status'],
                        'created_at': info['created_at'],
                        'natural_language_goal': info['natural_language_goal']
                    })
            
            # 按创建时间倒序排列
            missions.sort(key=lambda x: x['created_at'], reverse=True)
            
            # 分页
            if offset > 0:
                missions = missions[offset:]
            if limit is not None:
                missions = missions[:limit]
            
            return missions
    
    def get_missions_by_status(self, status: MissionStatus) -> List[Mission]:
        """获取指定状态的所有任务（完整数据）"""
        missions = []
        
        with self._cache_lock:
            mission_ids = [
                mission_id for mission_id, info in self._index_cache.items()
                if info['status'] == status.value
            ]
        
        for mission_id in mission_ids:
            mission = self.get_mission(mission_id)
            if mission:
                missions.append(mission)
        
        return missions
    
    def count_missions_by_status(self) -> Dict[str, int]:
        """统计各状态任务数量"""
        counts = {}
        
        with self._cache_lock:
            for info in self._index_cache.values():
                status = info['status']
                counts[status] = counts.get(status, 0) + 1
        
        return counts
    
    def get_recent_missions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的任务"""
        return self.list_missions(limit=limit)
    
    def search_missions(self, keyword: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """搜索任务"""
        with self._cache_lock:
            missions = []
            
            keyword_lower = keyword.lower()
            for mission_id, info in self._index_cache.items():
                if (keyword_lower in mission_id.lower() or 
                    keyword_lower in info['natural_language_goal'].lower()):
                    missions.append({
                        'mission_id': mission_id,
                        'status': info['status'],
                        'created_at': info['created_at'],
                        'natural_language_goal': info['natural_language_goal']
                    })
            
            # 按创建时间倒序排列
            missions.sort(key=lambda x: x['created_at'], reverse=True)
            
            if limit is not None:
                missions = missions[:limit]
            
            return missions
    
    def cleanup_old_missions(self, days: int = 30) -> int:
        """清理旧任务（已完成或失败的任务）"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        
        deleted_count = 0
        
        with self._cache_lock:
            mission_ids_to_delete = [
                mission_id for mission_id, info in self._index_cache.items()
                if (info['status'] in ['completed', 'failed'] and 
                    info['created_at'] < cutoff_iso)
            ]
        
        for mission_id in mission_ids_to_delete:
            if self.delete_mission(mission_id):
                deleted_count += 1
        
        logger.info(f"清理了 {deleted_count} 个旧任务")
        return deleted_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        status_counts = self.count_missions_by_status()
        
        with self._cache_lock:
            total_missions = len(self._index_cache)
            
            # 计算今天创建的任务数
            today = datetime.now().date().isoformat()
            today_missions = sum(
                1 for info in self._index_cache.values()
                if info['created_at'].startswith(today)
            )
        
        return {
            'total_missions': total_missions,
            'today_missions': today_missions,
            'status_counts': status_counts,
            'active_missions': status_counts.get('pending', 0) + 
                             status_counts.get('planning', 0) + 
                             status_counts.get('executing', 0) + 
                             status_counts.get('reporting', 0) + 
                             status_counts.get('rendering', 0) + 
                             status_counts.get('notifying', 0)
        }
    
    def backup_missions(self, backup_dir: str) -> bool:
        """备份所有任务数据"""
        try:
            import shutil
            
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_path / f"missions_backup_{timestamp}.tar.gz"
            
            shutil.make_archive(
                str(backup_file.with_suffix('')),
                'gztar',
                str(self.missions_dir.parent),
                str(self.missions_dir.name)
            )
            
            logger.info(f"任务备份完成: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"任务备份失败: {e}")
            return False
    
    def restore_missions(self, backup_file: str) -> bool:
        """从备份恢复任务数据"""
        try:
            import shutil
            import tarfile
            
            # 创建临时目录
            temp_dir = self.missions_dir.parent / "temp_restore"
            temp_dir.mkdir(exist_ok=True)
            
            # 解压备份文件
            with tarfile.open(backup_file, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            # 移动文件
            restored_missions_dir = temp_dir / "missions"
            if restored_missions_dir.exists():
                # 备份当前数据
                current_backup = self.missions_dir.with_suffix('.backup')
                if self.missions_dir.exists():
                    shutil.move(str(self.missions_dir), str(current_backup))
                
                # 恢复数据
                shutil.move(str(restored_missions_dir), str(self.missions_dir))
                
                # 重建索引
                self._rebuild_index()
                
                # 清理临时目录
                shutil.rmtree(temp_dir)
                
                logger.info(f"任务恢复完成: {backup_file}")
                return True
            
        except Exception as e:
            logger.error(f"任务恢复失败: {e}")
            return False
    
    def get_all_missions(self) -> List[Mission]:
        """获取所有任务（完整数据）"""
        missions = []
        
        with self._cache_lock:
            mission_ids = list(self._index_cache.keys())
        
        for mission_id in mission_ids:
            mission = self.get_mission(mission_id)
            if mission:
                missions.append(mission)
        
        # 按创建时间倒序排列
        missions.sort(key=lambda x: x.created_at, reverse=True)
        return missions