"""
MyHelper Application Factory
负责创建Flask app实例，并在此初始化后台线程池 (ThreadPoolExecutor) 作为任务执行器
"""
from flask import Flask
from concurrent.futures import ThreadPoolExecutor
import logging
import os


def create_app(config_name='development'):
    """创建Flask应用实例"""
    app = Flask(__name__)
    
    # 加载配置
    from config.config import config
    app.config.from_object(config[config_name])
    
    # 初始化后台线程池
    app.thread_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix='myhelper-task')
    
    # 设置日志
    setup_logging(app)
    
    # 注册蓝图
    from app.apis.hooks import hooks_bp
    from app.apis.reports import reports_bp
    from app.web import web_bp
    app.register_blueprint(hooks_bp, url_prefix='/api/v1')
    app.register_blueprint(reports_bp, url_prefix='/api/v1')
    app.register_blueprint(web_bp)
    
    # 确保在应用关闭时清理线程池
    @app.teardown_appcontext
    def cleanup_thread_pool(error):
        if hasattr(app, 'thread_pool'):
            app.thread_pool.shutdown(wait=False)
    
    return app


def setup_logging(app):
    """设置应用日志"""
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = logging.FileHandler('logs/myhelper.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('MyHelper startup')