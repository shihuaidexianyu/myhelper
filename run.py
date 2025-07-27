"""
MyHelper应用启动脚本
从app工厂创建app并运行
"""
import os
import sys
from app import create_app
from app.utils.logging_utils import setup_logging


def main():
    """主函数"""
    # 获取配置环境
    config_name = os.environ.get('FLASK_ENV', 'development')
    
    # 创建应用
    app = create_app(config_name)
    
    # 设置日志
    setup_logging(app, app.config)
    
    # 获取运行参数
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5005))
    debug = app.config.get('DEBUG', False)
    
    app.logger.info(f"Starting MyHelper on {host}:{port} (debug={debug})")
    
    try:
        # 启动应用
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )
    except KeyboardInterrupt:
        app.logger.info("Application stopped by user")
    except Exception as e:
        app.logger.error(f"Application failed to start: {e}")
        sys.exit(1)
    finally:
        # 清理资源
        if hasattr(app, 'thread_pool'):
            app.logger.info("Shutting down thread pool...")
            app.thread_pool.shutdown(wait=True)


if __name__ == '__main__':
    main()