"""
通知管理器
负责发送任务结果通知
"""
import logging
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
from datetime import datetime

import requests


class NotificationManager:
    """通知管理器，处理各种类型的通知发送"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    def send_success(self, report_id: str, summary: str, context: Dict[str, Any] = None):
        """发送成功通知"""
        message = {
            'type': 'success',
            'report_id': report_id,
            'message': f'Task completed successfully: {summary}',
            'timestamp': datetime.utcnow().isoformat(),
            'context': context or {}
        }
        
        self._send_notification(message)
    
    def send_failure(self, report_id: str, error_details: Dict[str, Any], context: Dict[str, Any] = None):
        """发送失败通知"""
        message = {
            'type': 'failure',
            'report_id': report_id,
            'message': f'Task failed: {error_details.get("message", "Unknown error")}',
            'error_details': error_details,
            'timestamp': datetime.utcnow().isoformat(),
            'context': context or {}
        }
        
        self._send_notification(message)
    
    def send_warning(self, report_id: str, warning_message: str, context: Dict[str, Any] = None):
        """发送警告通知"""
        message = {
            'type': 'warning',
            'report_id': report_id,
            'message': warning_message,
            'timestamp': datetime.utcnow().isoformat(),
            'context': context or {}
        }
        
        self._send_notification(message)
    
    def _send_notification(self, message: Dict[str, Any]):
        """发送通知到所有配置的渠道"""
        # 记录到日志
        self._log_notification(message)
        
        # 发送邮件通知
        if self.config.get('email', {}).get('enabled', False):
            self._send_email_notification(message)
        
        # 发送Webhook通知
        if self.config.get('webhook', {}).get('enabled', False):
            self._send_webhook_notification(message)
        
        # 发送Slack通知
        if self.config.get('slack', {}).get('enabled', False):
            self._send_slack_notification(message)
    
    def _log_notification(self, message: Dict[str, Any]):
        """记录通知到日志"""
        level = {
            'success': logging.INFO,
            'failure': logging.ERROR,
            'warning': logging.WARNING
        }.get(message['type'], logging.INFO)
        
        self.logger.log(level, f"Notification [{message['type']}]: {message['message']}")
    
    def _send_email_notification(self, message: Dict[str, Any]):
        """发送邮件通知"""
        try:
            email_config = self.config['email']
            
            # 创建邮件内容
            msg = MIMEMultipart()
            msg['From'] = email_config['from']
            msg['To'] = ', '.join(email_config['to'])
            msg['Subject'] = f"MyHelper Notification [{message['type'].upper()}] - {message['report_id']}"
            
            # 构建邮件正文
            body = self._format_email_body(message)
            msg.attach(MIMEText(body, 'html'))
            
            # 发送邮件
            with smtplib.SMTP(email_config['smtp_host'], email_config['smtp_port']) as server:
                if email_config.get('use_tls', True):
                    server.starttls()
                if email_config.get('username') and email_config.get('password'):
                    server.login(email_config['username'], email_config['password'])
                
                server.send_message(msg)
            
            self.logger.info(f"Email notification sent for report {message['report_id']}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
    
    def _send_webhook_notification(self, message: Dict[str, Any]):
        """发送Webhook通知"""
        try:
            webhook_config = self.config['webhook']
            
            # 发送POST请求
            response = requests.post(
                webhook_config['url'],
                json=message,
                headers=webhook_config.get('headers', {}),
                timeout=webhook_config.get('timeout', 10)
            )
            
            response.raise_for_status()
            self.logger.info(f"Webhook notification sent for report {message['report_id']}")
            
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")
    
    def _send_slack_notification(self, message: Dict[str, Any]):
        """发送Slack通知"""
        try:
            slack_config = self.config['slack']
            
            # 构建Slack消息格式
            slack_message = {
                'text': message['message'],
                'attachments': [{
                    'color': self._get_slack_color(message['type']),
                    'fields': [
                        {
                            'title': 'Report ID',
                            'value': message['report_id'],
                            'short': True
                        },
                        {
                            'title': 'Timestamp',
                            'value': message['timestamp'],
                            'short': True
                        }
                    ]
                }]
            }
            
            # 添加错误详情
            if message['type'] == 'failure' and 'error_details' in message:
                slack_message['attachments'][0]['fields'].append({
                    'title': 'Error Details',
                    'value': json.dumps(message['error_details'], indent=2),
                    'short': False
                })
            
            # 发送到Slack
            response = requests.post(
                slack_config['webhook_url'],
                json=slack_message,
                timeout=slack_config.get('timeout', 10)
            )
            
            response.raise_for_status()
            self.logger.info(f"Slack notification sent for report {message['report_id']}")
            
        except Exception as e:
            self.logger.error(f"Failed to send slack notification: {e}")
    
    def _format_email_body(self, message: Dict[str, Any]) -> str:
        """格式化邮件正文"""
        color = {
            'success': '#28a745',
            'failure': '#dc3545',
            'warning': '#ffc107'
        }.get(message['type'], '#6c757d')
        
        body = f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: {color}; color: white; padding: 20px; text-align: center;">
                    <h2>MyHelper Notification</h2>
                    <p style="font-size: 18px; margin: 0;">{message['type'].upper()}</p>
                </div>
                
                <div style="padding: 20px; background-color: #f8f9fa;">
                    <h3>Message</h3>
                    <p>{message['message']}</p>
                    
                    <h3>Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Report ID</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{message['report_id']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Timestamp</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{message['timestamp']}</td>
                        </tr>
        """
        
        # 添加错误详情
        if message['type'] == 'failure' and 'error_details' in message:
            body += f"""
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Error Details</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">
                                <pre>{json.dumps(message['error_details'], indent=2)}</pre>
                            </td>
                        </tr>
            """
        
        body += """
                    </table>
                </div>
                
                <div style="padding: 20px; text-align: center; color: #6c757d; font-size: 12px;">
                    <p>This is an automated message from MyHelper. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return body
    
    def _get_slack_color(self, notification_type: str) -> str:
        """获取Slack消息颜色"""
        return {
            'success': 'good',
            'failure': 'danger',
            'warning': 'warning'
        }.get(notification_type, '#000000')