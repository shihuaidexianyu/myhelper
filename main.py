#!/usr/bin/env python3
"""
MyHelper: 轻量化自包含的异步智能任务平台
主入口文件
"""

import os
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.web.api import create_app
from app.core.worker import Worker
from app.core.config_manager import ConfigManager
from app.utils.logging import setup_logger


def main():
    """主程序入口"""
    # 设置日志
    logger = setup_logger("myhelper", "data/logs/myhelper.log")

    # 初始化配置管理器
    config_manager = ConfigManager()

    # 创建Flask应用
    app = create_app(config_manager)

    # 启动后台工作线程
    worker = Worker(config_manager)
    worker.start()  # 使用start方法而不是直接运行

    # 从配置读取服务器参数
    host = config_manager.get("web.host", "0.0.0.0")
    port = config_manager.get("web.port", 5000)
    debug = config_manager.get("web.debug", False)

    logger.info("MyHelper启动成功")
    logger.info(f"Web界面: http://localhost:{port}")

    # 启动Flask开发服务器
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    main()
