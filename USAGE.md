# MyHelper 使用指南

MyHelper是一个轻量化自包含的异步智能任务平台，使用Flask + Jinja2构建，支持自然语言任务规划和自动化执行。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

#### 2.1 基础配置

编辑 `config/default.json` 文件，设置基本配置：

```json
{
  "system": {
    "name": "MyHelper",
    "version": "1.0.0",
    "queue_check_interval": 5,
    "max_retries": 3,
    "task_timeout": 3600
  },
  "web": {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false
  }
}
```

#### 2.2 LLM配置（必需）

设置OpenAI API密钥以启用智能任务规划：

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "api_key": "your-openai-api-key-here",
    "api_base": "https://api.openai.com/v1"
  }
}
```

#### 2.3 通知配置（可选）

配置邮件和Slack通知：

```json
{
  "notifications": {
    "email": {
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "your-email@gmail.com",
      "password": "your-app-password",
      "from_email": "your-email@gmail.com"
    },
    "slack": {
      "webhook_url": "https://hooks.slack.com/services/...",
      "bot_name": "MyHelper"
    }
  }
}
```

### 3. 启动服务

```bash
python main.py
```

服务启动后，访问 http://localhost:5000 查看Web界面。

## 使用方法

### 3.1 通过Web界面创建任务

1. 访问 http://localhost:5000
2. 点击"创建任务"按钮
3. 输入自然语言描述的任务目标，例如：
   - "查询今天的天气并发送邮件通知"
   - "从数据库获取用户统计信息并生成报告"
   - "监控系统状态并在异常时发送告警"

### 3.2 通过API创建任务

```bash
curl -X POST http://localhost:5000/api/missions \\
  -H "Content-Type: application/json" \\
  -d '{
    "natural_language_goal": "查询系统状态并生成报告",
    "report_config": {
      "enabled": true,
      "template": "mission_report.html"
    },
    "notification_configs": [
      {
        "type": "email",
        "target": "admin@example.com",
        "enabled": true
      }
    ]
  }'
```

### 3.3 查看任务状态

- **Web界面**: 访问 http://localhost:5000/dashboard
- **API**: `GET /api/missions` 获取任务列表
- **单个任务**: `GET /api/missions/{mission_id}` 获取任务详情

## 架构说明

### 核心组件

1. **ConfigManager**: 配置管理，支持热重载
2. **MissionManager**: 任务数据管理，文件系统持久化
3. **QueueManager**: 任务队列管理，原子操作
4. **Worker**: 后台任务执行引擎
5. **LLMManager**: LLM API通信管理
6. **Agent框架**: 模块化的任务执行代理
7. **ReportGenerator**: HTML报告生成
8. **NotificationManager**: 多渠道通知支持

### 任务执行流程

1. **规划阶段**: 使用LLM将自然语言目标分解为结构化子任务
2. **执行阶段**: 按依赖关系执行子任务
3. **报告阶段**: 生成任务总结
4. **渲染阶段**: 生成HTML报告
5. **通知阶段**: 发送完成通知

### Agent类型

- **OrchestratorAgent**: 任务规划和编排
- **DataQueryAgent**: 数据查询和分析
- **ActionAgent**: 具体动作执行
- **ReportAgent**: 报告生成
- **NotificationAgent**: 通知发送
- **ValidationAgent**: 结果验证

## API文档

### 任务管理

#### 创建任务
```
POST /api/missions
Content-Type: application/json

{
  "natural_language_goal": "任务描述",
  "report_config": {
    "enabled": true,
    "template": "mission_report.html",
    "custom_css": ""
  },
  "notification_configs": [
    {
      "type": "email|slack|webhook|console",
      "target": "目标地址",
      "enabled": true,
      "config": {}
    }
  ]
}
```

#### 获取任务列表
```
GET /api/missions?page=1&per_page=20&status=pending
```

#### 获取任务详情
```
GET /api/missions/{mission_id}
```

#### 删除任务
```
DELETE /api/missions/{mission_id}
```

### 系统监控

#### 健康检查
```
GET /health
GET /api/health/detailed
```

#### 系统指标
```
GET /api/metrics
```

#### 日志查看
```
GET /api/logs?lines=100&level=ERROR
```

### Worker管理

#### Worker状态
```
GET /api/worker/status
```

#### 启动/停止Worker
```
POST /api/worker/start
POST /api/worker/stop
```

## 配置参考

### 完整配置示例

```json
{
  "system": {
    "name": "MyHelper",
    "version": "1.0.0",
    "queue_check_interval": 5,
    "max_retries": 3,
    "task_timeout": 3600,
    "backup_enabled": true,
    "backup_interval": 86400
  },
  "web": {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false,
    "secret_key": "change-this-in-production",
    "base_url": "http://localhost:5000"
  },
  "llm": {
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "api_base": "https://api.openai.com/v1",
    "api_key": "sk-...",
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
      "username": "your-email@gmail.com",
      "password": "your-app-password",
      "from_email": "your-email@gmail.com"
    },
    "slack": {
      "webhook_url": "https://hooks.slack.com/services/...",
      "bot_token": "xoxb-...",
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
    "enable_cors": true,
    "allowed_origins": ["*"],
    "rate_limit_enabled": false,
    "max_requests_per_minute": 60
  }
}
```

## 常见问题

### Q: 如何添加自定义Agent？

A: 继承`BaseAgent`类并实现`execute`方法：

```python
from app.agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self, tool_manager, llm_manager):
        super().__init__("CustomAgent", tool_manager, llm_manager)
    
    def execute(self, goal, context=None):
        # 实现自定义逻辑
        return self.create_success_result({"result": "success"})

# 注册Agent
agent_factory.register_agent("CustomAgent", CustomAgent)
```

### Q: 如何自定义报告模板？

A: 在`templates/reports/`目录下创建Jinja2模板文件：

```html
<!DOCTYPE html>
<html>
<head>
    <title>自定义报告 - {{ mission.mission_id }}</title>
</head>
<body>
    <h1>{{ mission.natural_language_goal }}</h1>
    <p>状态: {{ mission.status }}</p>
    <!-- 更多自定义内容 -->
</body>
</html>
```

### Q: 如何添加新的通知驱动？

A: 继承`NotificationDriver`类：

```python
from app.core.notification_manager import NotificationDriver

class CustomDriver(NotificationDriver):
    def send(self, message, target, config):
        # 实现发送逻辑
        return True
    
    def validate_config(self, config):
        # 验证配置
        return True

# 注册驱动
notification_manager.register_driver("custom", CustomDriver())
```

### Q: 如何备份和恢复数据？

A: 所有数据存储在`data/`目录下，可以直接备份整个目录：

```bash
# 备份
tar -czf myhelper-backup-$(date +%Y%m%d).tar.gz data/

# 恢复
tar -xzf myhelper-backup-20240101.tar.gz
```

## 故障排除

### 常见错误

1. **LLM连接失败**: 检查API密钥和网络连接
2. **Worker无法启动**: 检查文件权限和磁盘空间
3. **任务执行失败**: 查看日志文件`data/logs/myhelper.log`
4. **通知发送失败**: 检查通知配置和网络连接

### 日志分析

```bash
# 查看最近的错误日志
tail -f data/logs/myhelper.log | grep ERROR

# 查看Worker状态
curl http://localhost:5000/api/worker/status

# 查看系统健康状态
curl http://localhost:5000/api/health/detailed
```

## 性能优化

1. **调整队列检查间隔**: 减少`queue_check_interval`可提高响应速度
2. **启用备份**: 设置`backup_enabled`为true确保数据安全
3. **优化LLM调用**: 调整`temperature`和`max_tokens`参数
4. **定期清理**: 设置报告文件清理策略

## 安全建议

1. 更改默认的`secret_key`
2. 设置合适的CORS策略
3. 启用速率限制
4. 定期备份数据
5. 监控系统资源使用情况

## 扩展开发

MyHelper采用模块化设计，支持以下扩展：

- 自定义Agent类型
- 新的通知驱动
- 自定义报告模板
- 第三方服务集成
- 自定义工具和插件

更多技术细节请参考源代码和架构文档。