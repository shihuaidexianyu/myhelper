"""
Web后端API (BFF - Backend For Frontend)
提供RESTful API接口供前端调用
"""

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file
from functools import wraps
from typing import Dict, Any, Optional

from ..core.config_manager import ConfigManager
from ..core.mission_manager import MissionManager
from ..core.queue_manager import QueueManager
from ..core.worker import Worker
from ..core.models import Mission, ReportConfig, NotificationConfig

logger = logging.getLogger(__name__)


def create_app(config_manager: ConfigManager) -> Flask:
    """创建Flask应用"""
    # 获取项目根目录
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    app = Flask(__name__, 
                template_folder=os.path.join(project_root, 'templates'),
                static_folder=os.path.join(project_root, 'static'))
    
    # 配置Flask
    app.config['SECRET_KEY'] = config_manager.get('web.secret_key', 'myhelper-secret-key')
    app.config['JSON_AS_ASCII'] = False
    
    # 初始化组件
    mission_manager = MissionManager()
    queue_manager = QueueManager()
    worker = Worker(config_manager)
    
    # Worker将在main.py中启动，这里不自动启动
    
    # 错误处理装饰器
    def handle_errors(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"API错误 {request.endpoint}: {e}")
                return jsonify({
                    'error': str(e),
                    'success': False
                }), 500
        return decorated_function
    
    # API响应格式化
    def api_response(data=None, message="success", success=True, status_code=200):
        """标准API响应格式"""
        response = {
            'success': success,
            'message': message,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(response), status_code
    
    # ===================
    # 主页和基础路由
    # ===================
    
    @app.route('/')
    def index():
        """主页"""
        return render_template('index.html')
    
    @app.route('/dashboard')
    def dashboard():
        """仪表板"""
        return render_template('dashboard.html')
    
    @app.route('/health')
    def health_check():
        """健康检查"""
        try:
            worker_status = worker.get_worker_status()
            return api_response({
                'status': 'healthy',
                'worker': worker_status,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return api_response(
                message=f"健康检查失败: {e}",
                success=False,
                status_code=503
            )
    
    @app.route('/api/health/detailed')
    @handle_errors
    def detailed_health_check():
        """详细健康检查"""
        try:
            # Worker状态
            worker_status = worker.get_worker_status()
            
            # 配置状态
            config_status = {
                'loaded': True,
                'config_file_exists': config_manager.config_file.exists() if hasattr(config_manager, 'config_file') else True
            }
            
            # LLM连接状态
            llm_status = {
                'configured': bool(config_manager.get('llm.api_key')),
                'connection_test': worker.llm_manager.test_connection() if config_manager.get('llm.api_key') else False
            }
            
            # 文件系统状态
            filesystem_status = {
                'data_dir_writable': os.access('data', os.W_OK),
                'queue_dir_exists': os.path.exists('data/queue'),
                'logs_dir_exists': os.path.exists('data/logs')
            }
            
            # 通知驱动状态
            notification_status = worker.notification_manager.get_driver_status()
            
            health_data = {
                'overall_status': 'healthy',
                'worker': worker_status,
                'config': config_status,
                'llm': llm_status,
                'filesystem': filesystem_status,
                'notifications': notification_status,
                'timestamp': datetime.now().isoformat()
            }
            
            # 检查是否有任何组件不健康
            if not worker_status.get('running') or not filesystem_status.get('data_dir_writable'):
                health_data['overall_status'] = 'unhealthy'
                return api_response(health_data, status_code=503)
            
            return api_response(health_data)
            
        except Exception as e:
            return api_response(
                data={'overall_status': 'error', 'error': str(e)},
                message=f"健康检查失败: {e}",
                success=False,
                status_code=503
            )
    
    @app.route('/api/metrics')
    @handle_errors
    def get_metrics():
        """获取系统指标"""
        try:
            import psutil
            import time
            
            # 系统资源使用情况
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            # 应用指标
            missions = mission_manager.get_all_missions()
            queue_status = queue_manager.get_queue_status()
            worker_status = worker.get_worker_status()
            
            # LLM使用统计
            llm_stats = worker.llm_manager.get_usage_stats()
            
            # 通知历史
            notification_history = worker.notification_manager.get_notification_history(limit=10)
            
            metrics = {
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_total': memory.total,
                    'memory_used': memory.used,
                    'memory_percent': memory.percent,
                    'disk_total': disk.total,
                    'disk_used': disk.used,
                    'disk_percent': (disk.used / disk.total) * 100
                },
                'application': {
                    'total_missions': len(missions),
                    'queue_status': queue_status,
                    'worker_running': worker_status.get('running', False),
                    'uptime_seconds': time.time() - (getattr(worker, 'start_time', time.time()))
                },
                'llm': llm_stats,
                'notifications': {
                    'recent_count': len(notification_history),
                    'success_rate': sum(1 for n in notification_history if n.get('success')) / len(notification_history) if notification_history else 0
                },
                'timestamp': datetime.now().isoformat()
            }
            
            return api_response(metrics)
            
        except ImportError:
            # psutil not available, return basic metrics
            missions = mission_manager.get_all_missions()
            queue_status = queue_manager.get_queue_status()
            worker_status = worker.get_worker_status()
            
            basic_metrics = {
                'application': {
                    'total_missions': len(missions),
                    'queue_status': queue_status,
                    'worker_running': worker_status.get('running', False)
                },
                'timestamp': datetime.now().isoformat(),
                'note': 'Limited metrics - install psutil for full system metrics'
            }
            
            return api_response(basic_metrics)
        
        except Exception as e:
            return api_response(
                message=f"获取指标失败: {e}",
                success=False,
                status_code=500
            )
    
    @app.route('/api/logs')
    @handle_errors
    def get_logs():
        """获取最近的日志"""
        try:
            log_file = 'data/logs/myhelper.log'
            lines = request.args.get('lines', 100, type=int)
            level = request.args.get('level', '').upper()
            
            if not os.path.exists(log_file):
                return api_response(
                    data={'logs': [], 'message': '日志文件不存在'},
                    message="日志文件不存在"
                )
            
            # 读取日志文件的最后N行
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            # 获取最后的lines行
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            # 过滤日志级别
            if level:
                recent_lines = [line for line in recent_lines if level in line]
            
            logs_data = {
                'logs': [line.strip() for line in recent_lines],
                'total_lines': len(recent_lines),
                'log_file': log_file,
                'timestamp': datetime.now().isoformat()
            }
            
            return api_response(logs_data)
            
        except Exception as e:
            return api_response(
                message=f"获取日志失败: {e}",
                success=False,
                status_code=500
            )
    
    # ===================
    # 任务管理API
    # ===================
    
    @app.route('/api/missions', methods=['GET'])
    @handle_errors
    def get_missions():
        """获取任务列表"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        
        # 获取任务列表
        missions = mission_manager.get_all_missions()
        
        # 状态过滤
        if status:
            missions = [m for m in missions if m.status.value == status]
        
        # 分页
        total = len(missions)
        start = (page - 1) * per_page
        end = start + per_page
        missions_page = missions[start:end]
        
        return api_response({
            'missions': [mission.to_dict() for mission in missions_page],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
    
    @app.route('/api/missions/<mission_id>', methods=['GET'])
    @handle_errors
    def get_mission(mission_id: str):
        """获取单个任务详情"""
        mission = mission_manager.get_mission(mission_id)
        if not mission:
            return api_response(
                message="任务不存在",
                success=False,
                status_code=404
            )
        
        return api_response(mission.to_dict())
    
    @app.route('/api/missions', methods=['POST'])
    @handle_errors
    def create_mission():
        """创建新任务"""
        data = request.get_json()
        
        if not data or 'natural_language_goal' not in data:
            return api_response(
                message="缺少任务目标描述",
                success=False,
                status_code=400
            )
        
        # 创建任务
        mission = Mission.create_new(
            natural_language_goal=data['natural_language_goal']
        )
        
        # 配置报告生成
        if 'report_config' in data:
            report_config = data['report_config']
            mission.report_config = ReportConfig(
                enabled=report_config.get('enabled', True),
                template=report_config.get('template', 'mission_report.html'),
                custom_css=report_config.get('custom_css')
            )
        
        # 配置通知
        if 'notification_configs' in data:
            mission.notification_configs = []
            for config in data['notification_configs']:
                notification_config = NotificationConfig(
                    type=config['type'],
                    target=config['target'],
                    enabled=config.get('enabled', True),
                    config=config.get('config', {})
                )
                mission.notification_configs.append(notification_config)
        
        # 保存任务
        mission_manager.create_mission(mission)
        
        # 加入队列
        queue_manager.enqueue(mission.mission_id)
        
        logger.info(f"创建新任务: {mission.mission_id}")
        
        return api_response(
            data=mission.to_dict(),
            message="任务创建成功",
            status_code=201
        )
    
    @app.route('/api/missions/<mission_id>', methods=['DELETE'])
    @handle_errors
    def delete_mission(mission_id: str):
        """删除任务"""
        success = mission_manager.delete_mission(mission_id)
        if not success:
            return api_response(
                message="任务不存在或删除失败",
                success=False,
                status_code=404
            )
        
        return api_response(message="任务删除成功")
    
    # ===================
    # 队列管理API
    # ===================
    
    @app.route('/api/queue/status', methods=['GET'])
    @handle_errors
    def get_queue_status():
        """获取队列状态"""
        status = queue_manager.get_queue_status()
        return api_response(status)
    
    @app.route('/api/queue/retry/<mission_id>', methods=['POST'])
    @handle_errors
    def retry_mission(mission_id: str):
        """重试失败的任务"""
        mission = mission_manager.get_mission(mission_id)
        if not mission:
            return api_response(
                message="任务不存在",
                success=False,
                status_code=404
            )
        
        # 重置任务状态
        from ..core.models import MissionStatus
        mission.update_status(MissionStatus.PENDING)
        mission_manager.update_mission(mission)
        
        # 重新加入队列
        queue_manager.enqueue(mission_id)
        
        return api_response(message="任务已重新加入队列")
    
    # ===================
    # Worker管理API
    # ===================
    
    @app.route('/api/worker/status', methods=['GET'])
    @handle_errors
    def get_worker_status():
        """获取Worker状态"""
        status = worker.get_worker_status()
        return api_response(status)
    
    @app.route('/api/worker/start', methods=['POST'])
    @handle_errors
    def start_worker():
        """启动Worker"""
        worker.start()
        return api_response(message="Worker启动成功")
    
    @app.route('/api/worker/stop', methods=['POST'])
    @handle_errors
    def stop_worker():
        """停止Worker"""
        worker.stop()
        return api_response(message="Worker停止成功")
    
    # ===================
    # 统计信息API
    # ===================
    
    @app.route('/api/stats', methods=['GET'])
    @handle_errors
    def get_stats():
        """获取统计信息"""
        missions = mission_manager.get_all_missions()
        
        # 统计不同状态的任务数量
        status_count = {}
        for mission in missions:
            status = mission.status.value
            status_count[status] = status_count.get(status, 0) + 1
        
        # 队列状态
        queue_status = queue_manager.get_queue_status()
        
        # Worker状态
        worker_status = worker.get_worker_status()
        
        return api_response({
            'mission_stats': {
                'total': len(missions),
                'by_status': status_count
            },
            'queue_stats': queue_status,
            'worker_stats': worker_status
        })
    
    # ===================
    # 报告相关API
    # ===================
    
    @app.route('/api/reports/<mission_id>')
    @handle_errors
    def get_report(mission_id: str):
        """获取任务报告"""
        mission = mission_manager.get_mission(mission_id)
        if not mission:
            return api_response(
                message="任务不存在",
                success=False,
                status_code=404
            )
        
        # 检查是否有报告文件
        report_path = getattr(mission, 'report_path', None)
        if report_path and os.path.exists(report_path):
            return send_file(report_path, mimetype='text/html')
        
        # 如果没有报告文件，返回简单的任务信息
        return render_template('simple_report.html', mission=mission.to_dict())
    
    # ===================
    # 配置管理API
    # ===================
    
    @app.route('/api/config', methods=['GET'])
    @handle_errors
    def get_config():
        """获取配置信息"""
        # 只返回非敏感配置
        config = config_manager.get_all_config()
        
        # 移除敏感信息
        safe_config = {}
        for key, value in config.items():
            if 'password' not in key.lower() and 'secret' not in key.lower() and 'key' not in key.lower():
                safe_config[key] = value
        
        return api_response(safe_config)
    
    # ===================
    # 测试和调试API
    # ===================
    
    @app.route('/api/test/notification', methods=['POST'])
    @handle_errors
    def test_notification():
        """测试通知配置"""
        data = request.get_json()
        
        if not data or 'type' not in data or 'target' not in data:
            return api_response(
                message="缺少通知类型或目标",
                success=False,
                status_code=400
            )
        
        success = worker.notification_manager.test_notification(
            notification_type=data['type'],
            target=data['target']
        )
        
        return api_response({
            'test_result': success
        }, message="测试通知发送完成" if success else "测试通知发送失败")
    
    @app.route('/api/test/llm', methods=['POST'])
    @handle_errors
    def test_llm():
        """测试LLM连接"""
        success = worker.llm_manager.test_connection()
        
        return api_response({
            'test_result': success
        }, message="LLM连接正常" if success else "LLM连接失败")
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return api_response(
                message="API端点不存在",
                success=False,
                status_code=404
            )
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            return api_response(
                message="服务器内部错误",
                success=False,
                status_code=500
            )
        return render_template('500.html'), 500
    
    logger.info("Flask应用创建完成")
    return app