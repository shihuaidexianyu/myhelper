"""
日志配置工具
"""
import logging
import logging.handlers
import os
from datetime import datetime


def setup_logging(app=None, config=None):
    """设置应用日志"""
    if config is None and app:
        config = app.config
    
    log_level = getattr(config, 'LOG_LEVEL', 'INFO') if config else 'INFO'
    log_format = getattr(config, 'LOG_FORMAT', 
                        '%(asctime)s %(name)s %(levelname)s: %(message)s') if config else \
                        '%(asctime)s %(name)s %(levelname)s: %(message)s'
    
    # 确保日志目录存在
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # 设置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（按日期滚动）
    file_handler = logging.handlers.TimedRotatingFileHandler(
        'logs/myhelper.log',
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s %(name)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 错误日志文件处理器
    error_handler = logging.handlers.TimedRotatingFileHandler(
        'logs/myhelper_errors.log',
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # 设置第三方库日志级别
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    if app:
        app.logger.info('Logging setup completed')


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器"""
    return logging.getLogger(name)