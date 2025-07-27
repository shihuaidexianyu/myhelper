# MyHelper

轻量化自包含的异步智能任务平台 (含Web可视化界面)

## 快速开始

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 启动应用:
```bash
python main.py
```

3. 打开Web界面:
```
http://localhost:5000
```

## 项目结构

```
myhelper/
├── app/                # 应用核心代码
│   ├── core/          # 核心服务层
│   ├── web/           # Web应用层  
│   ├── agents/        # Agent框架
│   └── utils/         # 工具类
├── data/              # 持久化数据
│   ├── missions/      # 任务数据
│   ├── queue/         # 任务队列
│   ├── config/        # 配置文件
│   ├── results/       # 生成的报告
│   └── styles/        # CSS样式文件
├── static/            # 静态资源
└── templates/         # 模板文件
```

## 技术栈

- Backend: Flask + Jinja2
- Frontend: HTML/CSS/JavaScript
- 持久化: 文件系统
- 任务调度: APScheduler
- 无外部数据库依赖

## 版本

v0.1.0