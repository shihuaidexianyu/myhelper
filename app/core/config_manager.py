"""
配置管理器 - 系统配置的统一管理
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器 - 负责系统配置的读取、验证和热更新"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "default.json"
        self.lock = threading.RLock()
        self._config = {}
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        with self.lock:
            if self.config_file.exists():
                try:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        self._config = json.load(f)
                    logger.info(f"配置加载成功: {self.config_file}")
                except Exception as e:
                    logger.error(f"配置加载失败: {e}")
                    self._config = self._get_default_config()
            else:
                # 创建默认配置
                self._config = self._get_default_config()
                self._save_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "version": "0.1.0",
            "system": {
                "worker_threads": 1,
                "max_retries": 3,
                "retry_delay": 5,
                "task_timeout": 3600,
                "queue_check_interval": 5
            },
            "web": {
                "host": "0.0.0.0",
                "port": 5000,
                "debug": False
            },
            "llm": {
                "provider": "openai",
                "api_base": "https://api.openai.com/v1",
                "api_key": "",
                "model": "gpt-3.5-turbo",
                "max_tokens": 4000,
                "temperature": 0.7
            },
            "mcp_services": {
                "example_service": {
                    "url": "http://localhost:8001",
                    "api_key": "",
                    "timeout": 30
                }
            },
            "notifications": {
                "email": {
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "from_address": "",
                    "use_tls": True
                },
                "slack": {
                    "bot_token": "",
                    "signing_secret": ""
                },
                "webhook": {
                    "default_timeout": 30
                }
            },
            "cron_jobs": {
                "example_job": {
                    "cron": "0 9 * * MON",
                    "goal": "生成本周工作总结报告",
                    "enabled": False,
                    "report_config": {
                        "style": "default"
                    },
                    "notification_configs": []
                }
            },
            "security": {
                "allowed_hosts": ["*"],
                "cors_origins": ["*"],
                "max_request_size": 16777216
            },
            "logging": {
                "level": "INFO",
                "file": "data/logs/myhelper.log",
                "max_bytes": 10485760,
                "backup_count": 5
            }
        }
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            logger.info("配置保存成功")
        except Exception as e:
            logger.error(f"配置保存失败: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点分隔的嵌套键"""
        with self.lock:
            keys = key.split('.')
            value = self._config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
    
    def set(self, key: str, value: Any, save: bool = True):
        """设置配置值，支持点分隔的嵌套键"""
        with self.lock:
            keys = key.split('.')
            config = self._config
            
            # 导航到父级配置
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 设置值
            config[keys[-1]] = value
            
            if save:
                self._save_config()
    
    def update(self, updates: Dict[str, Any], save: bool = True):
        """批量更新配置"""
        with self.lock:
            for key, value in updates.items():
                self.set(key, value, save=False)
            
            if save:
                self._save_config()
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        with self.lock:
            return self._config.copy()
    
    def reload(self):
        """重新加载配置文件"""
        logger.info("重新加载配置...")
        self._load_config()
    
    def validate_config(self) -> bool:
        """验证配置的有效性"""
        try:
            # 验证必要的配置项
            required_sections = ['system', 'web', 'llm', 'notifications']
            for section in required_sections:
                if section not in self._config:
                    logger.error(f"缺少必要的配置节: {section}")
                    return False
            
            # 验证端口号
            port = self.get('web.port')
            if not isinstance(port, int) or port < 1 or port > 65535:
                logger.error(f"无效的端口号: {port}")
                return False
            
            # 验证工作线程数
            worker_threads = self.get('system.worker_threads')
            if not isinstance(worker_threads, int) or worker_threads < 1:
                logger.error(f"无效的工作线程数: {worker_threads}")
                return False
            
            # 验证Cron表达式
            cron_jobs = self.get('cron_jobs', {})
            for job_name, job_config in cron_jobs.items():
                if 'cron' in job_config:
                    if not self._validate_cron_expression(job_config['cron']):
                        logger.error(f"无效的Cron表达式: {job_name} - {job_config['cron']}")
                        return False
            
            logger.info("配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False
    
    def _validate_cron_expression(self, cron_expr: str) -> bool:
        """验证Cron表达式的基本格式"""
        try:
            from croniter import croniter
            return croniter.is_valid(cron_expr)
        except ImportError:
            # 如果没有croniter库，进行简单验证
            parts = cron_expr.strip().split()
            return len(parts) == 5
        except:
            return False
    
    def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        return self.get('llm', {})
    
    def get_mcp_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取MCP服务配置"""
        return self.get(f'mcp_services.{service_name}')
    
    def get_notification_config(self, notification_type: str) -> Optional[Dict[str, Any]]:
        """获取通知配置"""
        return self.get(f'notifications.{notification_type}')
    
    def get_cron_jobs(self) -> Dict[str, Any]:
        """获取定时任务配置"""
        return self.get('cron_jobs', {})
    
    def add_cron_job(self, job_name: str, cron_expr: str, goal: str, 
                     enabled: bool = True, report_config: Optional[Dict] = None,
                     notification_configs: Optional[list] = None):
        """添加定时任务"""
        job_config = {
            "cron": cron_expr,
            "goal": goal,
            "enabled": enabled,
            "report_config": report_config or {},
            "notification_configs": notification_configs or []
        }
        
        cron_jobs = self.get('cron_jobs', {})
        cron_jobs[job_name] = job_config
        self.set('cron_jobs', cron_jobs)
        
        logger.info(f"添加定时任务: {job_name}")
    
    def remove_cron_job(self, job_name: str):
        """删除定时任务"""
        cron_jobs = self.get('cron_jobs', {})
        if job_name in cron_jobs:
            del cron_jobs[job_name]
            self.set('cron_jobs', cron_jobs)
            logger.info(f"删除定时任务: {job_name}")
    
    def get_web_config(self) -> Dict[str, Any]:
        """获取Web配置"""
        return self.get('web', {})
    
    def get_system_config(self) -> Dict[str, Any]:
        """获取系统配置"""
        return self.get('system', {})