"""
配置管理
存放不同环境（开发、生产）的配置文件
"""
import os
from typing import Dict, Any


class Config:
    """基础配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'myhelper-secret-key-change-in-production'
    
    # 数据目录
    DATA_DIR = os.environ.get('DATA_DIR') or 'data'
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FORMAT = '%(asctime)s %(name)s %(levelname)s: %(message)s'
    
    # 线程池配置
    THREAD_POOL_MAX_WORKERS = int(os.environ.get('THREAD_POOL_MAX_WORKERS', '5'))
    
    # 通知配置
    NOTIFICATION_CONFIG = {
        'email': {
            'enabled': os.environ.get('EMAIL_NOTIFICATIONS_ENABLED', 'false').lower() == 'true',
            'smtp_host': os.environ.get('SMTP_HOST', 'localhost'),
            'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
            'use_tls': os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true',
            'username': os.environ.get('SMTP_USERNAME'),
            'password': os.environ.get('SMTP_PASSWORD'),
            'from': os.environ.get('SMTP_FROM', 'noreply@myhelper.local'),
            'to': [email.strip() for email in os.environ.get('NOTIFICATION_EMAILS', '').split(',') if email.strip()]
        },
        'webhook': {
            'enabled': os.environ.get('WEBHOOK_NOTIFICATIONS_ENABLED', 'false').lower() == 'true',
            'url': os.environ.get('WEBHOOK_URL'),
            'headers': {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {os.environ.get('WEBHOOK_TOKEN')}" if os.environ.get('WEBHOOK_TOKEN') else None
            },
            'timeout': int(os.environ.get('WEBHOOK_TIMEOUT', '10'))
        },
        'slack': {
            'enabled': os.environ.get('SLACK_NOTIFICATIONS_ENABLED', 'false').lower() == 'true',
            'webhook_url': os.environ.get('SLACK_WEBHOOK_URL'),
            'timeout': int(os.environ.get('SLACK_TIMEOUT', '10'))
        }
    }
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        pass


class DevelopmentConfig(Config):
    """开发环境配置"""
    
    DEBUG = True
    
    # 开发环境使用更详细的日志
    LOG_LEVEL = 'DEBUG'
    
    # 开发环境使用较少的线程池
    THREAD_POOL_MAX_WORKERS = 2
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # 开发环境特殊初始化
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(name)s %(levelname)s: %(message)s'
        )


class ProductionConfig(Config):
    """生产环境配置"""
    
    DEBUG = False
    
    # 生产环境使用INFO级别日志
    LOG_LEVEL = 'INFO'
    
    # 生产环境使用更多线程池
    THREAD_POOL_MAX_WORKERS = int(os.environ.get('THREAD_POOL_MAX_WORKERS', '10'))
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # 生产环境日志配置
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/myhelper.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)


class TestingConfig(Config):
    """测试环境配置"""
    
    TESTING = True
    DEBUG = True
    
    # 测试环境使用内存数据
    DATA_DIR = 'test_data'
    
    # 测试环境不需要线程池
    THREAD_POOL_MAX_WORKERS = 1
    
    # 测试环境禁用通知
    NOTIFICATION_CONFIG = {
        'email': {'enabled': False},
        'webhook': {'enabled': False},
        'slack': {'enabled': False}
    }
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # 测试环境日志配置
        import logging
        logging.basicConfig(
            level=logging.WARNING,  # 测试时减少日志输出
            format='%(name)s %(levelname)s: %(message)s'
        )


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}