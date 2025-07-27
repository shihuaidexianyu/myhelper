"""
报告生成器 - 将任务执行结果生成美观的HTML报告
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template
from .models import Mission, MissionStatus, SubtaskStatus

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器 - 负责将任务结果渲染为HTML格式"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        
        # 报告输出目录
        self.output_dir = config_manager.get('reports.output_dir', 'data/reports')
        self.templates_dir = config_manager.get('reports.templates_dir', 'templates/reports')
        
        # 确保目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # 初始化Jinja2环境
        self.jinja_env = None
        self._init_jinja_environment()
        
        # 默认模板
        self._ensure_default_templates()
        
        logger.info("ReportGenerator初始化完成")
    
    def _init_jinja_environment(self):
        """初始化Jinja2模板环境"""
        try:
            self.jinja_env = Environment(
                loader=FileSystemLoader(self.templates_dir),
                autoescape=True
            )
            
            # 添加自定义过滤器
            self.jinja_env.filters['format_datetime'] = self._format_datetime
            self.jinja_env.filters['status_badge'] = self._status_badge
            self.jinja_env.filters['duration_format'] = self._duration_format
            
        except Exception as e:
            logger.error(f"初始化Jinja2环境失败: {e}")
            raise
    
    def _ensure_default_templates(self):
        """确保默认模板存在"""
        default_template_path = os.path.join(self.templates_dir, 'mission_report.html')
        
        if not os.path.exists(default_template_path):
            logger.info("创建默认报告模板")
            self._create_default_template(default_template_path)
    
    def _create_default_template(self, template_path: str):
        """创建默认报告模板"""
        default_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MyHelper 任务报告 - {{ mission.mission_id }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .header .subtitle {
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }
        .content {
            padding: 30px;
        }
        .mission-info {
            background: #f8f9fa;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 30px;
        }
        .mission-info h2 {
            margin-top: 0;
            color: #495057;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
            text-transform: uppercase;
        }
        .status-completed { background: #d4edda; color: #155724; }
        .status-failed { background: #f8d7da; color: #721c24; }
        .status-pending { background: #fff3cd; color: #856404; }
        .status-executing { background: #cce5ff; color: #004085; }
        .subtasks {
            margin-top: 30px;
        }
        .subtask {
            border: 1px solid #e9ecef;
            border-radius: 6px;
            margin-bottom: 15px;
            overflow: hidden;
        }
        .subtask-header {
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .subtask-content {
            padding: 20px;
        }
        .meta-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e9ecef;
        }
        .meta-item {
            text-align: center;
        }
        .meta-item .label {
            font-size: 0.9em;
            color: #6c757d;
            margin-bottom: 5px;
        }
        .meta-item .value {
            font-size: 1.2em;
            font-weight: 600;
            color: #495057;
        }
        .summary {
            background: #e7f3ff;
            border-left: 4px solid #007bff;
            padding: 20px;
            margin: 30px 0;
            border-radius: 0 6px 6px 0;
        }
        .summary h3 {
            margin-top: 0;
            color: #0056b3;
        }
        .footer {
            text-align: center;
            padding: 20px;
            color: #6c757d;
            font-size: 0.9em;
            border-top: 1px solid #e9ecef;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>MyHelper 任务报告</h1>
            <div class="subtitle">{{ mission.natural_language_goal }}</div>
        </div>
        
        <div class="content">
            <div class="mission-info">
                <h2>任务概览</h2>
                <p><strong>任务ID:</strong> {{ mission.mission_id }}</p>
                <p><strong>状态:</strong> {{ mission.status | status_badge }}</p>
                <p><strong>创建时间:</strong> {{ mission.created_at | format_datetime }}</p>
                {% if mission.completed_at %}
                <p><strong>完成时间:</strong> {{ mission.completed_at | format_datetime }}</p>
                <p><strong>执行耗时:</strong> {{ (mission.completed_at, mission.created_at) | duration_format }}</p>
                {% endif %}
            </div>

            {% if mission.final_summary %}
            <div class="summary">
                <h3>任务总结</h3>
                <p>{{ mission.final_summary }}</p>
            </div>
            {% endif %}

            {% if mission.subtask_graph %}
            <div class="subtasks">
                <h2>子任务详情 ({{ mission.subtask_graph | length }}个)</h2>
                {% for subtask in mission.subtask_graph %}
                <div class="subtask">
                    <div class="subtask-header">
                        <div>
                            <strong>{{ subtask.goal }}</strong>
                            <span style="margin-left: 15px; color: #6c757d; font-size: 0.9em;">
                                {{ subtask.subagent_name }}
                            </span>
                        </div>
                        <div>{{ subtask.status | status_badge }}</div>
                    </div>
                    {% if subtask.result or subtask.error_message %}
                    <div class="subtask-content">
                        {% if subtask.result %}
                        <p><strong>执行结果:</strong></p>
                        <pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto;">{{ subtask.result | string }}</pre>
                        {% endif %}
                        {% if subtask.error_message %}
                        <p><strong>错误信息:</strong></p>
                        <div style="color: #dc3545; background: #f8d7da; padding: 10px; border-radius: 4px;">
                            {{ subtask.error_message }}
                        </div>
                        {% endif %}
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            {% endif %}

            <div class="meta-info">
                <div class="meta-item">
                    <div class="label">子任务总数</div>
                    <div class="value">{{ mission.subtask_graph | length }}</div>
                </div>
                <div class="meta-item">
                    <div class="label">已完成</div>
                    <div class="value">{{ mission.subtask_graph | selectattr('status', 'equalto', 'completed') | list | length }}</div>
                </div>
                <div class="meta-item">
                    <div class="label">失败</div>
                    <div class="value">{{ mission.subtask_graph | selectattr('status', 'equalto', 'failed') | list | length }}</div>
                </div>
                <div class="meta-item">
                    <div class="label">成功率</div>
                    <div class="value">
                        {% if mission.subtask_graph | length > 0 %}
                        {{ "%.1f" | format((mission.subtask_graph | selectattr('status', 'equalto', 'completed') | list | length) / (mission.subtask_graph | length) * 100) }}%
                        {% else %}
                        0%
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>报告生成时间: {{ report_generated_at | format_datetime }}</p>
            <p>Powered by MyHelper - 智能任务自动化平台</p>
        </div>
    </div>
</body>
</html>"""
        
        try:
            os.makedirs(os.path.dirname(template_path), exist_ok=True)
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(default_template)
            logger.info(f"默认模板创建成功: {template_path}")
        except Exception as e:
            logger.error(f"创建默认模板失败: {e}")
            raise
    
    def generate_report(self, mission: Mission, template_name: str = 'mission_report.html') -> str:
        """生成任务报告"""
        try:
            logger.info(f"开始生成报告: {mission.mission_id}")
            
            # 准备模板数据
            template_data = self._prepare_template_data(mission)
            
            # 加载模板
            template = self.jinja_env.get_template(template_name)
            
            # 渲染HTML
            html_content = template.render(**template_data)
            
            # 保存报告文件
            report_path = self._save_report(mission.mission_id, html_content)
            
            logger.info(f"报告生成完成: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"生成报告失败 {mission.mission_id}: {e}")
            raise
    
    def _prepare_template_data(self, mission: Mission) -> Dict[str, Any]:
        """准备模板数据"""
        return {
            'mission': mission.to_dict(),
            'report_generated_at': datetime.now(),
            'config': self.config_manager.get_all_config()
        }
    
    def _save_report(self, mission_id: str, html_content: str) -> str:
        """保存报告文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{mission_id}_{timestamp}.html"
        report_path = os.path.join(self.output_dir, filename)
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return report_path
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            raise
    
    def generate_report_url(self, mission_id: str) -> str:
        """生成报告访问URL"""
        base_url = self.config_manager.get('web.base_url', 'http://localhost:5000')
        return f"{base_url}/reports/{mission_id}"
    
    def _format_datetime(self, dt) -> str:
        """格式化日期时间"""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except:
                return dt
        
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return str(dt)
    
    def _status_badge(self, status) -> str:
        """生成状态徽章HTML"""
        status_str = str(status).lower()
        badge_class = f"status-badge status-{status_str}"
        
        status_text_map = {
            'completed': '已完成',
            'failed': '失败', 
            'pending': '待处理',
            'executing': '执行中',
            'planning': '规划中',
            'reporting': '报告中',
            'rendering': '渲染中',
            'notifying': '通知中'
        }
        
        display_text = status_text_map.get(status_str, status_str)
        return f'<span class="{badge_class}">{display_text}</span>'
    
    def _duration_format(self, time_tuple) -> str:
        """格式化时间差"""
        try:
            end_time, start_time = time_tuple
            
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            
            if isinstance(end_time, datetime) and isinstance(start_time, datetime):
                duration = end_time - start_time
                total_seconds = int(duration.total_seconds())
                
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                
                if hours > 0:
                    return f"{hours}小时{minutes}分钟{seconds}秒"
                elif minutes > 0:
                    return f"{minutes}分钟{seconds}秒"
                else:
                    return f"{seconds}秒"
        except:
            pass
        
        return "未知"
    
    def get_available_templates(self) -> list:
        """获取可用模板列表"""
        try:
            templates = []
            for filename in os.listdir(self.templates_dir):
                if filename.endswith('.html'):
                    templates.append(filename)
            return templates
        except Exception as e:
            logger.error(f"获取模板列表失败: {e}")
            return ['mission_report.html']
    
    def cleanup_old_reports(self, days: int = 30):
        """清理旧报告文件"""
        try:
            import time
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            
            for filename in os.listdir(self.output_dir):
                if filename.endswith('.html'):
                    filepath = os.path.join(self.output_dir, filename)
                    if os.path.getmtime(filepath) < cutoff_time:
                        os.remove(filepath)
                        logger.info(f"清理旧报告: {filename}")
        except Exception as e:
            logger.error(f"清理旧报告失败: {e}")