### **MyHelper**

#### **1. 系统总览与核心设计理念**

MyHelper(v0.1.0) 的核心架构变更，是从一个依赖外部消息队列的分布式系统，演变为一个更内聚、更易于部署的单体（Monolithic）应用。所有任务的生命周期管理都在主Web应用进程内的后台线程中完成。

* **设计哲学**：
  * **简化性（Simplicity）**: 移除消息队列等外部依赖，降低了部署和维护的复杂度，特别适合初期和中小型部署场景。
  * **响应性（Responsiveness）**: API端点通过异步执行任务，能够立即响应客户端，提供了良好的用户体验。
  * **安全性（Security）**：MyHelper控制协议 (MCP) 和 `ToolManager` 构成了系统的安全基石。所有工具的调用都必须通过这个严格的、基于权限和参数校验的网关，防止不安全的操作。
  * **模块化（Modularity）**: 尽管是单体应用，但内部逻辑依然遵循高内聚、低耦合的原则。`MasterAgent` 负责编排，`PlannerAgent`、`ExecutorAgent`、`ReporterAgent` 各司其职，`ToolManager` 专注工具执行。这种划分使得系统易于理解、维护和扩展。

#### **2. 项目目录结构**

目录结构保持不变，但在此对各部分职责进行更清晰的界定。

```
myhelper_v3/
├── app/
│   ├── __init__.py             # 应用工厂。负责创建Flask app实例，并在此初始化后台线程池 (ThreadPoolExecutor) 作为任务执行器，并将其注册到app上下文中。
│   ├── agents/                 # 包含所有Agent的核心逻辑实现 (Master, Planner, Executor, Reporter)。
│   ├── apis/                   # API蓝图。定义所有HTTP接口，如 /api/v1/hooks/<task_id> 用于任务触发，以及 /api/v1/reports/<report_id> 用于状态查询。
│   ├── core/                   # 核心管理器模块。
│   │   ├── tool_manager.py     # 工具管理器，MCP的实现者。
│   │   ├── storage_manager.py  # 数据存储管理器，负责所有对data/目录中JSON文件的读写操作，并处理并发安全问题。
│   │   └── notification_manager.py # 通知管理器，负责发送任务结果通知。
│   ├── models/                 # 定义系统中使用的数据结构（如Task, Report, MCPRequest等），可以使用Pydantic或简单字典。
│   └── utils/                  # 通用工具函数，如日志配置、时间处理等。
├── config/                     # 存放不同环境（开发、生产）的配置文件。
├── data/                       # 简易文件数据库。
│   ├── tasks.json              # 任务定义库。
│   ├── tools.json              # 授权工具库。
│   ├── reports/                # 存放每个任务执行报告的目录，每个报告一个JSON文件。
│   └── learnings/              # 存放每次任务执行后生成的学习经验的目录。
├── logs/                       # 日志文件目录。
├── run.py                      # 应用启动脚本，从app工厂创建app并运行。
└── requirements.txt            # 项目依赖。
```

#### **3. MyHelper控制协议 (MCP) 详解**

此部分作为系统内部通信的“法律”，其稳定性和严格性至关重要。

* **角色**: MCP是 `ExecutorAgent` 与 `ToolManager` 之间唯一的通信方式。它将一个抽象的“计划步骤”转化为一个具体的、可验证的、可执行的“指令”。
* **安全含义**: 任何不符合MCP结构、或`tool_name`未授权、或`params`不满足`tools.json`中定义的请求，都将在 `ToolManager` 层被直接拒绝。这创建了一个清晰的安全边界。

#### **4. 核心组件详细设计**

##### **4.1. `app.core.storage_manager.py` - 数据存储管理器**

* **定位**: 系统的持久化层抽象，负责所有文件I/O，是保证数据一致性和线程安全的关键。
* **核心职责**:
    1. 提供对 `data/` 目录中所有JSON文件的增、删、改、查接口。
    2. **实现线程安全**: 由于多项任务可能在不同线程中并发读写文件，`StorageManager` 必须为每个核心数据文件（或整个`data`目录）实现文件锁或读写锁 (`threading.Lock` 或 `threading.RLock`)，以防止数据竞争和文件损坏。
    3. 抽象文件路径，上层逻辑（如Agents）只关心数据ID，不关心具体文件位置。
* **主要接口**:
  * `get_task(task_id)`: 从 `tasks.json` 读取任务定义。
  * `get_tool(tool_name)`: 从 `tools.json` 读取工具定义。
  * `get_authorized_tools(tool_ids)`: 根据任务授权的ID列表，获取完整的工具定义列表。
  * `create_report(task_id, trigger_context)`: 在 `data/reports/` 目录中创建一个新的报告文件（如 `<uuid>.json`），初始状态为 `queued`，并返回唯一的 `report_id` (通常是文件名)。
  * `update_report(report_id, data)`: 更新指定报告文件的内容（如状态、日志、结果）。
  * `get_report(report_id)`: 读取并返回指定报告的内容。
  * `save_learning(learning_data)`: 将新的学习经验保存到 `data/learnings/`。

##### **4.2. `app.apis.hooks.py` - API & 任务触发器**

* **定位**: 系统的唯一外部入口，负责接收HTTP请求并启动后台任务。
* **核心职责**:
    1. 定义 `/api/v1/hooks/<task_id>` POST 端点。
    2. 接收和验证请求。
    3. 启动后台任务。
    4. 立即返回，不阻塞客户端。
* **处理流程**:
    1. **接收请求**: 收到对 `/api/v1/hooks/<task_id>` 的 POST 请求。请求体中包含 `trigger_context` (触发任务的上下文信息，如Git提交哈希、用户参数等)。
    2. **参数校验**: 从URL中提取 `task_id`。
    3. **任务验证**: 调用 `StorageManager.get_task(task_id)`。如果任务不存在，返回 `404 Not Found`。
    4. **创建初始报告**: 调用 `StorageManager.create_report(task_id, trigger_context)`。此操作会生成并返回一个唯一的 `report_id`。这是关键一步，确保了即使后台任务启动失败，也有一个可追踪的记录。
    5. **提交后台任务**:
          * 从Flask应用上下文中获取预先初始化的 `ThreadPoolExecutor`。
          * 构造一个 `MasterAgent` 实例或一个调用 `MasterAgent` 的函数。
          * 调用 `executor.submit(run_master_agent_task, task_id, trigger_context, report_id)`。
    6. **立即响应**: 向客户端返回 `202 Accepted` HTTP状态码，响应体为 `{"status": "queued", "report_id": report_id}`。

##### **4.3. `app.agents.master_agent.py` - 任务总协调官**

* **定位**: 任务执行的“大脑”，在一个独立的后台线程中运行，负责编排整个任务的生命周期。
* **输入**: 在初始化时接收 `task_id`, `trigger_context`, `report_id`。
* **核心职责**:
    1. 加载所有必要的数据。
    2. 管理任务状态流转。
    3. 依次调用`PlannerAgent`, `ExecutorAgent`, `ReporterAgent`。
    4. 处理所有子组件的成功和失败情况。
    5. 确保最终结果被妥善保存和通知。
* **处理流程 (`run_full_lifecycle` 方法)**:
    1. **初始化与状态更新**:
          * 实例化 `StorageManager` 和 `NotificationManager`。
          * 调用 `storage_manager.update_report(report_id, {"status": "running"})`。
    2. **数据加载**:
          * `task = storage_manager.get_task(task_id)`。
          * `authorized_tools = storage_manager.get_authorized_tools(task['authorized_tool_ids'])`。
          * 加载相关长期记忆（`learnings`）。
    3. **try...except 块开始**:
        4\.  **规划 (Planning)**:
        \* `planner = PlannerAgent(task, trigger_context, learnings)`。
        \* `plan = planner.generate_plan()`。
        \* 将生成的计划保存到报告中: `storage_manager.update_report(report_id, {"plan": plan})`。
        5\.  **执行 (Execution)**:
        \* `executor = ExecutorAgent()`。
        \* `execution_log = executor.execute(plan, authorized_tools)`。
        \* 将执行日志实时或最终保存到报告中: `storage_manager.update_report(report_id, {"execution_log": execution_log})`。
        6\.  **结果判断**:
        \* 检查 `execution_log` 的最终状态。如果为 `failed`，则构造一个包含失败原因的异常并 `raise`。
        7\.  **报告与学习 (Reporting & Learning)**:
        \* `reporter = ReporterAgent(plan, execution_log)`。
        \* `final_summary, new_learnings = reporter.generate_report_and_learnings()`。
        8\.  **归档 (Archiving)**:
        \* `storage_manager.update_report(report_id, {"status": "success", "summary": final_summary})`。
        \* `storage_manager.save_learning(new_learnings)`。
        9\.  **通知 (Notification)**:
        \* `notification_manager.send_success(report_id, final_summary)`。
    4. **except Exception as e 块**:
          * 记录详细的错误日志。
          * `error_details = {"error_type": type(e).__name__, "message": str(e)}`。
          * `storage_manager.update_report(report_id, {"status": "failed", "error": error_details})`。
          * `notification_manager.send_failure(report_id, error_details)`。

##### **4.4. `app.agents.executor_agent.py` - 命令执行官**

* **定位**: 将抽象计划转化为具体行动的执行者。
* **输入**: `plan` (来自PlannerAgent), `authorized_tools` (来自MasterAgent)。
* **核心职责**:
    1. 遍历计划中的每一个步骤。
    2. 将每个步骤转换为一个合法的MCP请求。
    3. 将MCP请求发送给 `ToolManager`。
    4. 记录每次工具调用的详细结果（成功、失败、输出、错误）。
    5. 根据步骤定义处理重试逻辑。
    6. 如果任何关键步骤失败，则中止执行。
* **输出**: `execution_log` (一个详细的、包含所有步骤执行情况的结构化日志)。

##### **4.5. `app.core.tool_manager.py` - 工具管理器与安全网关**

* **定位**: 系统的安全核心，所有具体操作的唯一执行入口。
* **输入**: 一个MCP结构的请求对象。
* **核心职责**:
    1. **协议校验**: 检查请求是否符合MCP的 `protocol` 和 `version`。
    2. **权限校验**: 检查MCP请求中的 `tool_name` 是否存在于当前任务授权的工具列表中 (此列表由 `ExecutorAgent` 在调用时传入或 `ToolManager` 自行获取)。
    3. **参数校验**:
          * 从 `tools.json` 中加载该工具的 `parameters` 定义。
          * 检查所有 `required: true` 的参数是否存在于MCP请求的 `params` 中。
          * 校验每个参数的 `type` 是否匹配。
          * 未来可扩展：执行更复杂的校验，如正则表达式匹配、数值范围检查等。
    4. **处理器分发**: 根据工具定义中的 `type` (如 `shell_command`, `http_request`, `python_function`)，将请求分发给相应的内部处理器。
    5. **沙箱化执行**:
          * 对于 `shell_command`，在执行命令时应用安全措施，例如：指定工作目录、设置超时、限制可执行命令的路径、以低权限用户运行。
          * 对于其他类型，也应考虑其安全上下文。
    6. **结果标准化**: 无论哪个处理器执行，都返回一个统一格式的结果对象，如 `{"status": "success/failed", "output": "...", "error": "..."}`。
* **输出**: 一个包含执行状态和结果的字典。

#### **5. 数据模型 (`data/*.json`)**

* **`tasks.json`**:
  * 定义了可被触发的任务。
  * 每个任务对象应包含 `id`, `name`, `description`, 以及 `authorized_tool_ids` 列表，明确此任务能够调用哪些工具。
* **`tools.json`**:
  * 系统的工具库，是 `ToolManager` 进行参数校验的依据。
  * `parameters` 数组是其核心，详细定义了每个参数的 `name`, `type`, `description`, `required` 属性。
* **`reports/<report_id>.json`**:
  * 任务执行的完整快照。
  * 结构应包含：`report_id`, `task_id`, `status` (`queued`, `running`, `success`, `failed`), `trigger_context`, `timestamps` (`created_at`, `started_at`, `finished_at`), `plan`, `execution_log`, `final_summary`, `error_details`。
* **`learnings/*.json`**:
  * 结构化知识。可以是成功模式的泛化、失败原因的分析等，供 `PlannerAgent` 在未来任务中参考。
