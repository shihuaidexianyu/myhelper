"""
通知管理器 - 支持多种通知渠道的统一接口
"""

import logging
import smtplib
import json
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class NotificationDriver(ABC):
    """通知驱动基类"""
    
    @abstractmethod
    def send(self, message: str, target: str, config: Dict[str, Any]) -> bool:
        """发送通知"""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        pass


class EmailDriver(NotificationDriver):
    """邮件通知驱动"""
    
    def send(self, message: str, target: str, config: Dict[str, Any]) -> bool:
        """发送邮件通知"""
        try:
            # 邮件服务器配置
            smtp_server = config.get('smtp_server', 'smtp.gmail.com')
            smtp_port = config.get('smtp_port', 587)
            username = config.get('username')
            password = config.get('password')
            from_email = config.get('from_email', username)
            
            if not username or not password:
                logger.error("邮件配置缺少用户名或密码")
                return False
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = target
            msg['Subject'] = config.get('subject', 'MyHelper 任务通知')
            
            # 添加邮件内容
            body = self._format_email_content(message, config)
            msg.attach(MIMEText(body, 'html' if config.get('html', True) else 'plain'))
            
            # 发送邮件
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            
            logger.info(f"邮件发送成功: {target}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证邮件配置"""
        required_fields = ['username', 'password']
        return all(field in config for field in required_fields)
    
    def _format_email_content(self, message: str, config: Dict[str, Any]) -> str:
        """格式化邮件内容"""
        if config.get('html', True):
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .header {{ background: #667eea; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .footer {{ background: #f8f9fa; padding: 10px; text-align: center; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>MyHelper 任务通知</h2>
                </div>
                <div class="content">
                    {message}
                </div>
                <div class="footer">
                    <p>发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Powered by MyHelper - 智能任务自动化平台</p>
                </div>
            </body>
            </html>
            """
        else:
            return f"{message}\n\n发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nPowered by MyHelper"


class SlackDriver(NotificationDriver):
    """Slack通知驱动"""
    
    def send(self, message: str, target: str, config: Dict[str, Any]) -> bool:
        """发送Slack通知"""
        try:
            webhook_url = config.get('webhook_url')
            bot_token = config.get('bot_token')
            
            if webhook_url:
                return self._send_via_webhook(message, target, webhook_url, config)
            elif bot_token:
                return self._send_via_api(message, target, bot_token, config)
            else:
                logger.error("Slack配置缺少webhook_url或bot_token")
                return False
                
        except Exception as e:
            logger.error(f"Slack发送失败: {e}")
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证Slack配置"""
        return 'webhook_url' in config or 'bot_token' in config
    
    def _send_via_webhook(self, message: str, target: str, webhook_url: str, config: Dict[str, Any]) -> bool:
        """通过Webhook发送"""
        payload = {
            "text": message,
            "channel": target,
            "username": config.get('bot_name', 'MyHelper'),
            "icon_emoji": config.get('icon_emoji', ':robot_face:'),
            "attachments": [
                {
                    "color": config.get('color', 'good'),
                    "footer": "MyHelper",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        
        logger.info(f"Slack Webhook发送成功: {target}")
        return True
    
    def _send_via_api(self, message: str, target: str, bot_token: str, config: Dict[str, Any]) -> bool:
        """通过API发送"""
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "channel": target,
            "text": message,
            "username": config.get('bot_name', 'MyHelper'),
            "icon_emoji": config.get('icon_emoji', ':robot_face:')
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if not result.get('ok'):
            raise Exception(f"Slack API错误: {result.get('error')}")
        
        logger.info(f"Slack API发送成功: {target}")
        return True


class WebhookDriver(NotificationDriver):
    """Webhook通知驱动"""
    
    def send(self, message: str, target: str, config: Dict[str, Any]) -> bool:
        """发送Webhook通知"""
        try:
            method = config.get('method', 'POST').upper()
            headers = config.get('headers', {'Content-Type': 'application/json'})
            
            # 准备请求数据
            payload = self._prepare_payload(message, target, config)
            
            # 发送请求
            if method == 'GET':
                response = requests.get(target, params=payload, headers=headers, timeout=10)
            else:
                response = requests.post(target, json=payload, headers=headers, timeout=10)
            
            response.raise_for_status()
            
            logger.info(f"Webhook发送成功: {target}")
            return True
            
        except Exception as e:
            logger.error(f"Webhook发送失败: {e}")
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证Webhook配置"""
        return True  # Webhook配置相对灵活
    
    def _prepare_payload(self, message: str, target: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """准备请求载荷"""
        template = config.get('payload_template', {
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'source': 'MyHelper'
        })
        
        # 支持模板变量替换
        if isinstance(template, dict):
            payload = {}
            for key, value in template.items():
                if isinstance(value, str):
                    payload[key] = value.replace('{{message}}', message).replace('{{timestamp}}', datetime.now().isoformat())
                else:
                    payload[key] = value
            return payload
        
        return template


class ConsoleDriver(NotificationDriver):
    """控制台通知驱动（主要用于测试）"""
    
    def send(self, message: str, target: str, config: Dict[str, Any]) -> bool:
        """输出到控制台"""
        try:
            formatted_message = f"[NOTIFICATION] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -> {target}: {message}"
            print(formatted_message)
            logger.info(formatted_message)
            return True
        except Exception as e:
            logger.error(f"控制台输出失败: {e}")
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """控制台驱动无需特殊配置"""
        return True


class NotificationManager:
    """通知管理器 - 统一管理各种通知驱动"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        
        # 注册驱动
        self.drivers = {
            'email': EmailDriver(),
            'slack': SlackDriver(),
            'webhook': WebhookDriver(),
            'console': ConsoleDriver()
        }
        
        # 通知历史记录
        self.notification_history = []
        
        logger.info("NotificationManager初始化完成")
    
    def send_notification(self, notification_type: str, target: str, message: str, 
                         config: Optional[Dict[str, Any]] = None) -> bool:
        """发送通知"""
        try:
            logger.info(f"发送通知: {notification_type} -> {target}")
            
            # 获取驱动
            driver = self.drivers.get(notification_type.lower())
            if not driver:
                logger.error(f"不支持的通知类型: {notification_type}")
                return False
            
            # 获取配置
            driver_config = config or self._get_notification_config(notification_type)
            
            # 验证配置
            if not driver.validate_config(driver_config):
                logger.error(f"通知配置无效: {notification_type}")
                return False
            
            # 发送通知
            success = driver.send(message, target, driver_config)
            
            # 记录历史
            self._record_notification(notification_type, target, message, success)
            
            return success
            
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
            return False
    
    def send_mission_notification(self, mission_data: Dict[str, Any], 
                                notification_configs: List[Dict[str, Any]]) -> Dict[str, bool]:
        """发送任务相关通知"""
        results = {}
        
        try:
            # 准备通知消息
            message = self._prepare_mission_message(mission_data)
            
            # 逐个发送通知
            for config in notification_configs:
                notification_type = config.get('type')
                target = config.get('target')
                
                if not notification_type or not target:
                    logger.warning(f"通知配置不完整: {config}")
                    continue
                
                success = self.send_notification(
                    notification_type=notification_type,
                    target=target,
                    message=message,
                    config=config.get('config', {})
                )
                
                results[f"{notification_type}:{target}"] = success
            
            return results
            
        except Exception as e:
            logger.error(f"发送任务通知失败: {e}")
            return {}
    
    def _get_notification_config(self, notification_type: str) -> Dict[str, Any]:
        """获取通知配置"""
        return self.config_manager.get(f'notifications.{notification_type}', {})
    
    def _prepare_mission_message(self, mission_data: Dict[str, Any]) -> str:
        """准备任务通知消息"""
        mission_id = mission_data.get('mission_id', '未知')
        goal = mission_data.get('natural_language_goal', '未知任务')
        status = mission_data.get('status', '未知状态')
        
        # 基础消息
        message = f"任务通知\\n\\n"
        message += f"任务ID: {mission_id}\\n"
        message += f"任务目标: {goal}\\n"
        message += f"当前状态: {status}\\n"
        
        # 添加时间信息
        if mission_data.get('completed_at'):
            message += f"完成时间: {mission_data['completed_at']}\\n"
        
        # 添加总结信息
        if mission_data.get('final_summary'):
            message += f"\\n任务总结:\\n{mission_data['final_summary']}\\n"
        
        # 添加报告链接
        if mission_data.get('result_page_url'):
            message += f"\\n详细报告: {mission_data['result_page_url']}\\n"
        
        return message
    
    def _record_notification(self, notification_type: str, target: str, 
                           message: str, success: bool):
        """记录通知历史"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'type': notification_type,
            'target': target,
            'message': message[:100] + '...' if len(message) > 100 else message,
            'success': success
        }
        
        self.notification_history.append(record)
        
        # 保持历史记录数量
        max_history = self.config_manager.get('notifications.max_history', 1000)
        if len(self.notification_history) > max_history:
            self.notification_history = self.notification_history[-max_history:]
    
    def get_notification_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取通知历史"""
        return self.notification_history[-limit:]
    
    def get_available_drivers(self) -> List[str]:
        """获取可用驱动列表"""
        return list(self.drivers.keys())
    
    def register_driver(self, name: str, driver: NotificationDriver):
        """注册自定义驱动"""
        self.drivers[name] = driver
        logger.info(f"注册通知驱动: {name}")
    
    def test_notification(self, notification_type: str, target: str) -> bool:
        """测试通知配置"""
        test_message = f"MyHelper通知测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_notification(notification_type, target, test_message)
    
    def get_driver_status(self) -> Dict[str, Dict[str, Any]]:
        """获取驱动状态"""
        status = {}
        
        for name, driver in self.drivers.items():
            config = self._get_notification_config(name)
            status[name] = {
                'available': True,
                'configured': driver.validate_config(config),
                'config_keys': list(config.keys()) if config else []
            }
        
        return status