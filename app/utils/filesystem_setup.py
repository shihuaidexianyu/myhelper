"""
文件系统持久化层设置
确保所有必要的目录和文件结构存在
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class FileSystemSetup:
    """文件系统设置管理器"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        
    def setup_directory_structure(self):
        """设置完整的目录结构"""
        directories = [
            # 数据目录
            'data',
            'data/missions',
            'data/queue',
            'data/queue/pending',
            'data/queue/processing', 
            'data/queue/completed',
            'data/queue/failed',
            'data/logs',
            'data/config',
            'data/reports',
            'data/backups',
            
            # 模板目录
            'templates',
            'templates/reports',
            
            # 静态文件目录
            'static',
            'static/css',
            'static/js',
            'static/images',
            
            # 配置目录
            'config',
            
            # 临时目录
            'tmp'
        ]
        
        created_dirs = []
        for directory in directories:
            dir_path = self.base_dir / directory
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(str(dir_path))
                logger.info(f"创建目录: {dir_path}")
        
        if created_dirs:
            logger.info(f"共创建 {len(created_dirs)} 个目录")
        else:
            logger.info("所有目录已存在")
            
        return created_dirs
    
    def setup_default_config(self):
        """设置默认配置文件"""
        config_file = self.base_dir / 'config' / 'default.json'
        
        if config_file.exists():
            logger.info("配置文件已存在，跳过创建")
            return
        
        default_config = {
            "system": {
                "name": "MyHelper",
                "version": "1.0.0",
                "queue_check_interval": 5,
                "max_retries": 3,
                "task_timeout": 3600,
                "backup_enabled": True,
                "backup_interval": 86400
            },
            "web": {
                "host": "0.0.0.0",
                "port": 5000,
                "debug": False,
                "secret_key": "myhelper-secret-key-change-in-production",
                "base_url": "http://localhost:5000"
            },
            "llm": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "api_base": "https://api.openai.com/v1",
                "api_key": "",
                "max_tokens": 4000,
                "temperature": 0.7,
                "timeout": 60
            },
            "reports": {
                "output_dir": "data/reports",
                "templates_dir": "templates/reports",
                "cleanup_days": 30
            },
            "notifications": {
                "max_history": 1000,
                "email": {
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "from_email": ""
                },
                "slack": {
                    "webhook_url": "",
                    "bot_token": "",
                    "bot_name": "MyHelper",
                    "icon_emoji": ":robot_face:"
                }
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "max_file_size": 10485760,
                "backup_count": 5
            },
            "security": {
                "enable_cors": True,
                "allowed_origins": ["*"],
                "rate_limit_enabled": False,
                "max_requests_per_minute": 60
            }
        }
        
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"创建默认配置文件: {config_file}")
    
    def setup_gitignore(self):
        """设置.gitignore文件"""
        gitignore_file = self.base_dir / '.gitignore'
        
        gitignore_content = """# MyHelper generated files
data/
tmp/
*.log

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Config with secrets
config/local.json
config/production.json
.env
"""
        
        if not gitignore_file.exists():
            with open(gitignore_file, 'w', encoding='utf-8') as f:
                f.write(gitignore_content)
            logger.info(f"创建.gitignore文件: {gitignore_file}")
    
    def setup_readme(self):
        """设置README文件"""
        readme_file = self.base_dir / 'README.md'
        
        if readme_file.exists():
            logger.info("README.md已存在，跳过创建")
            return
        
        readme_content = """# MyHelper

MyHelper是一个轻量化自包含的异步智能任务平台，使用Flask + Jinja2构建，支持自然语言任务规划和自动化执行。

## 特性

- 🤖 智能任务规划：使用LLM将自然语言目标分解为结构化子任务
- ⚡ 异步执行：基于队列的异步任务处理
- 📊 可视化报告：美观的HTML报告生成
- 🔔 多渠道通知：支持邮件、Slack、Webhook等通知方式
- 🌐 Web界面：直观的任务管理和监控界面
- 📁 文件系统持久化：无需外部数据库

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置LLM API密钥：
编辑 `config/default.json` 文件，设置OpenAI API密钥

3. 启动服务：
```bash
python main.py
```

4. 访问Web界面：
打开浏览器访问 http://localhost:5000

## 目录结构

```
myhelper/
├── app/                    # 应用核心代码
│   ├── core/              # 核心组件
│   ├── agents/            # Agent框架
│   ├── web/               # Web接口
│   └── utils/             # 工具函数
├── data/                  # 数据目录
│   ├── missions/          # 任务数据
│   ├── queue/             # 队列文件
│   ├── logs/              # 日志文件
│   └── reports/           # 报告文件
├── templates/             # HTML模板
├── config/                # 配置文件
└── main.py               # 程序入口
```

## API文档

### 任务管理
- `GET /api/missions` - 获取任务列表
- `POST /api/missions` - 创建新任务
- `GET /api/missions/{id}` - 获取任务详情
- `DELETE /api/missions/{id}` - 删除任务

### 系统监控
- `GET /health` - 健康检查
- `GET /api/stats` - 获取统计信息
- `GET /api/worker/status` - 获取Worker状态

## 配置说明

主要配置文件位于 `config/default.json`，包含以下配置：

- `system`: 系统基础配置
- `web`: Web服务配置
- `llm`: LLM API配置
- `reports`: 报告生成配置
- `notifications`: 通知配置

## 许可证

MIT License
"""
        
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        logger.info(f"创建README文件: {readme_file}")
    
    def setup_requirements(self):
        """设置requirements.txt文件"""
        requirements_file = self.base_dir / 'requirements.txt'
        
        if requirements_file.exists():
            logger.info("requirements.txt已存在，跳过创建")
            return
        
        requirements_content = """Flask==3.0.0
Jinja2==3.1.2
APScheduler==3.10.4
requests==2.31.0
python-dotenv==1.0.0
fcntl-py==0.2.0
"""
        
        with open(requirements_file, 'w', encoding='utf-8') as f:
            f.write(requirements_content)
        
        logger.info(f"创建requirements.txt文件: {requirements_file}")
    
    def setup_queue_files(self):
        """设置队列相关文件"""
        queue_base = self.base_dir / 'data' / 'queue'
        
        # 创建队列状态文件
        status_file = queue_base / 'status.json'
        if not status_file.exists():
            status_data = {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "last_updated": "1970-01-01T00:00:00Z"
            }
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=2)
            logger.info(f"创建队列状态文件: {status_file}")
        
        # 创建各队列目录的.gitkeep文件
        queue_dirs = ['pending', 'processing', 'completed', 'failed']
        for queue_dir in queue_dirs:
            gitkeep_file = queue_base / queue_dir / '.gitkeep'
            if not gitkeep_file.exists():
                gitkeep_file.touch()
                logger.info(f"创建.gitkeep文件: {gitkeep_file}")
    
    def verify_permissions(self):
        """验证目录权限"""
        critical_dirs = [
            'data',
            'data/missions',
            'data/queue',
            'data/logs',
            'data/reports'
        ]
        
        permission_issues = []
        for directory in critical_dirs:
            dir_path = self.base_dir / directory
            if dir_path.exists():
                if not os.access(dir_path, os.R_OK | os.W_OK):
                    permission_issues.append(str(dir_path))
        
        if permission_issues:
            logger.warning(f"以下目录可能存在权限问题: {permission_issues}")
        else:
            logger.info("目录权限检查通过")
        
        return permission_issues
    
    def setup_all(self):
        """执行完整的文件系统设置"""
        logger.info("开始设置文件系统...")
        
        # 创建目录结构
        self.setup_directory_structure()
        
        # 设置配置文件
        self.setup_default_config()
        
        # 设置项目文件
        self.setup_gitignore()
        self.setup_readme()
        self.setup_requirements()
        
        # 设置队列文件
        self.setup_queue_files()
        
        # 验证权限
        self.verify_permissions()
        
        logger.info("文件系统设置完成")
    
    def get_directory_info(self) -> Dict[str, Any]:
        """获取目录信息"""
        info = {
            'base_directory': str(self.base_dir),
            'directories': {},
            'total_size': 0
        }
        
        for item in self.base_dir.rglob('*'):
            if item.is_dir():
                info['directories'][str(item.relative_to(self.base_dir))] = {
                    'exists': True,
                    'writable': os.access(item, os.W_OK),
                    'file_count': len(list(item.iterdir())) if item.exists() else 0
                }
            elif item.is_file():
                try:
                    info['total_size'] += item.stat().st_size
                except:
                    pass
        
        return info


def setup_filesystem(base_dir: str = None):
    """文件系统设置的便捷函数"""
    setup = FileSystemSetup(base_dir)
    setup.setup_all()
    return setup.get_directory_info()


if __name__ == '__main__':
    # 直接运行时执行设置
    setup_filesystem()