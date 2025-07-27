# MyHelper

MyHelper v0.1.0 是一个基于Flask的任务自动化系统，采用单体架构设计，支持通过HTTP API触发任务执行。

## 核心特性

- **简化性**: 移除外部依赖，降低部署复杂度
- **响应性**: 异步执行任务，立即响应客户端
- **安全性**: 基于MCP协议的严格权限控制
- **模块化**: 高内聚、低耦合的内部架构

## 架构概览

```
MyHelper 由以下核心组件组成：
├── Master Agent    # 任务总协调官
├── Planner Agent   # 规划代理
├── Executor Agent  # 执行代理
├── Reporter Agent  # 报告代理
├── Tool Manager    # 工具管理器（MCP实现）
├── Storage Manager # 存储管理器
└── Notification Manager # 通知管理器
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
export FLASK_ENV=development
export DATA_DIR=data
export LOG_LEVEL=INFO
```

### 3. 启动应用

```bash
python run.py
```

应用将在 `http://localhost:5000` 启动。

## API 接口

### 触发任务

```bash
POST /api/v1/hooks/<task_id>
Content-Type: application/json

{
  "trigger_context": {
    "branch": "main",
    "environment": "production"
  }
}
```

### 查询报告

```bash
GET /api/v1/reports/<report_id>
```

### 查询任务状态

```bash
GET /api/v1/reports/<report_id>/status
```

### 列出所有任务

```bash
GET /api/v1/hooks
```

## 配置说明

### 任务配置 (data/tasks.json)

```json
{
  "task_id": {
    "id": "task_id",
    "name": "任务名称",
    "description": "任务描述",
    "authorized_tool_ids": ["tool1", "tool2"]
  }
}
```

### 工具配置 (data/tools.json)

```json
{
  "tool_id": {
    "id": "tool_id",
    "name": "工具名称",
    "type": "shell_command|http_request|python_function",
    "description": "工具描述",
    "command": "命令模板",
    "timeout": 30,
    "parameters": [...]
  }
}
```

## 环境变量配置

| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| FLASK_ENV | development | 运行环境 |
| HOST | 0.0.0.0 | 绑定地址 |
| PORT | 5000 | 监听端口 |
| DATA_DIR | data | 数据目录 |
| LOG_LEVEL | INFO | 日志级别 |
| THREAD_POOL_MAX_WORKERS | 5 | 线程池大小 |

### 通知配置

#### 邮件通知
```bash
EMAIL_NOTIFICATIONS_ENABLED=true
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USERNAME=user
SMTP_PASSWORD=pass
SMTP_FROM=noreply@example.com
NOTIFICATION_EMAILS=admin@example.com
```

#### Webhook通知
```bash
WEBHOOK_NOTIFICATIONS_ENABLED=true
WEBHOOK_URL=https://example.com/webhook
WEBHOOK_TOKEN=your-token
```

#### Slack通知
```bash
SLACK_NOTIFICATIONS_ENABLED=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## 目录结构

```
myhelper/
├── app/
│   ├── __init__.py           # 应用工厂
│   ├── agents/               # 代理模块
│   ├── apis/                 # API蓝图
│   ├── core/                 # 核心管理器
│   ├── models/               # 数据模型
│   └── utils/                # 工具函数
├── config/                   # 配置文件
├── data/                     # 数据存储
│   ├── tasks.json            # 任务定义
│   ├── tools.json            # 工具定义
│   ├── reports/              # 执行报告
│   └── learnings/            # 学习经验
├── logs/                     # 日志文件
├── run.py                    # 启动脚本
└── requirements.txt          # 依赖列表
```

## MCP 协议

MyHelper控制协议（MCP）是系统内部通信的标准格式：

```json
{
  "protocol": "MCP",
  "version": "1.0",
  "tool_name": "git_pull",
  "params": {
    "branch": "main"
  },
  "request_id": "uuid"
}
```

## 生产部署

### 使用Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app('production')"
```

### Docker部署

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app('production')"]
```

## 开发指南

### 添加新工具

1. 在 `data/tools.json` 中定义工具
2. 根据工具类型实现相应的处理逻辑
3. 在任务中授权使用该工具

### 添加新任务

1. 在 `data/tasks.json` 中定义任务
2. 指定任务可使用的工具列表
3. 通过API触发任务执行

## 监控和日志

- 应用日志：`logs/myhelper.log`
- 错误日志：`logs/myhelper_errors.log`
- 执行报告：`data/reports/`
- 学习经验：`data/learnings/`

## 故障排除

### 常见问题

1. **任务无法触发**: 检查任务ID是否存在于 `tasks.json`
2. **工具执行失败**: 检查工具定义和权限配置
3. **通知未发送**: 检查通知配置和网络连接

### 日志分析

```bash
# 查看最近的错误
tail -f logs/myhelper_errors.log

# 查看应用日志
tail -f logs/myhelper.log
```

## 版本信息

- 版本: v0.1.0
- Python要求: >=3.7
- Flask版本: 2.3.3

## 许可证

MIT License