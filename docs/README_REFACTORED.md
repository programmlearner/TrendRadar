# TrendRadar 重构版使用说明

## 项目概述

TrendRadar 是一个热点新闻聚合与智能分析平台,已完成从单文件（4000+ 行）到模块化架构的重构。新架构采用分层设计、SOLID 原则和插件化模式,具有更好的可维护性和可扩展性。

**核心功能**:
- 多平台热点新闻聚合 (知乎、微博、抖音、bilibili等 11+ 平台)
- 关键词筛选与权重排序
- 多渠道推送 (飞书、钉钉、企业微信、Telegram、邮件、ntfy)
- RESTful API 服务
- 可视化前端仪表板
- AI 智能分析 (基于大模型的对话分析)
- YouTube 热门视频监控
- 内置定时任务调度器

## 目录结构

```
TrendRadar/
├── src/                    # 核心代码
│   ├── models/             # 数据模型
│   │   └── news.py         # News, NewsStatistic, WordGroupStatistic
│   ├── core/               # 核心业务逻辑
│   │   ├── config.py       # 配置管理 (ConfigManager)
│   │   ├── filter.py       # 关键词筛选 (NewsFilter)
│   │   ├── ranking.py      # 权重计算和排序 (NewsRanking)
│   │   ├── reporter.py     # 报告生成 (NewsReporter)
│   │   └── push_record.py  # 推送记录管理 (PushRecordManager)
│   ├── sources/            # 信息源（插件化）
│   │   ├── base.py         # BaseSource 抽象基类
│   │   ├── newsnow.py      # NewNowSource (默认信息源)
│   │   ├── rss.py          # RSSSource (RSS 订阅源)
│   │   ├── youtube.py      # YouTubeSource (YouTube 热门视频)
│   │   └── registry.py     # SourceRegistry 注册器
│   ├── notifiers/          # 通知渠道（插件化）
│   │   ├── base.py         # BaseNotifier 抽象基类
│   │   ├── manager.py      # NotificationManager
│   │   ├── batch_sender.py # BatchSender 分批发送工具
│   │   ├── feishu.py       # 飞书通知
│   │   ├── dingtalk.py     # 钉钉通知
│   │   ├── wework.py       # 企业微信通知
│   │   ├── telegram.py     # Telegram 通知
│   │   ├── email.py        # 邮件通知
│   │   └── ntfy.py         # ntfy 通知
│   ├── api/                # API 服务（FastAPI）
│   │   ├── server.py       # FastAPI 应用入口
│   │   ├── routes/         # API 路由
│   │   │   ├── chat.py     # AI 对话接口
│   │   │   ├── system.py   # 系统状态查询接口
│   │   │   ├── dashboard.py # 仪表板数据接口
│   │   │   └── scheduler.py # 调度器管理接口
│   │   ├── scheduler/      # 任务调度器
│   │   │   └── task_scheduler.py # 定时任务调度器
│   │   ├── services/       # 业务服务层
│   │   │   ├── chat_service.py    # AI 对话服务
│   │   │   ├── llm_service.py     # 大模型服务
│   │   │   └── context_builder.py # 上下文构建器
│   │   ├── storage/        # 数据存储
│   │   │   └── json_store.py # JSON 会话存储
│   │   └── models/         # API 数据模型
│   │       └── schemas.py  # Pydantic 数据模型
│   ├── utils/              # 工具函数
│   │   ├── time.py         # 时间处理 (北京时间)
│   │   ├── file.py         # 文件操作
│   │   └── http.py         # HTTP 客户端
│   └── app.py              # TrendRadarApp 主应用类
├── mcp_server/             # MCP 协议服务器（独立模块,已废弃）
│   ├── server.py           # FastMCP 入口
│   ├── tools/              # 13 个 MCP 工具
│   ├── services/           # 数据服务层
│   └── utils/              # MCP 工具函数
├── config/                 # 配置文件
│   ├── config.yaml         # 主配置文件
│   └── frequency_words.txt # 关键词筛选配置
├── hotspot_dashboard/      # 前端可视化仪表板
│   ├── index.html          # 主页面
│   ├── css/                # 样式文件
│   └── js/                 # JavaScript 代码
├── output/                 # 数据输出目录（运行时生成）
│   ├── news_{date}.txt     # 文本格式报告
│   └── news_{date}.html    # HTML 格式报告
├── tests/                  # 单元测试（87+ 测试用例）
├── scripts/                # 工具脚本
├── docs/                   # 文档目录
├── main.py                 # 命令行入口（爬虫模式）
├── main_legacy.py          # 原始单文件版本（备份）
├── start_api.sh/bat        # API 服务启动脚本
├── stop_api.sh/bat         # API 服务停止脚本
└── status_api.sh/bat       # API 服务状态查询
```

## 快速开始

### 1. 爬虫模式（命令行）

```bash
# 使用默认配置运行（daily 模式）
python main.py

# 指定运行模式
python main.py --mode current      # 当前榜单模式
python main.py --mode incremental  # 增量监控模式

# 查看信息
python main.py --list-sources      # 列出所有信息源
python main.py --list-notifiers    # 列出通知渠道配置状态
python main.py --show-config       # 显示配置摘要
```

### 2. API 服务模式

#### 启动 API 服务

```bash
# Linux/macOS
./start_api.sh

# Windows
start_api.bat

# 手动启动
python -m src.api.server
```

#### 访问方式

- **API 文档**: http://localhost:8000/docs (Swagger UI)
- **前端仪表板**: http://localhost:8000/ (访问 hotspot_dashboard/index.html)
- **ReDoc 文档**: http://localhost:8000/redoc

#### 停止服务

```bash
# Linux/macOS
./stop_api.sh

# Windows
stop_api.bat
```

#### 查看状态

```bash
# Linux/macOS
./status_api.sh

# Windows
status_api.bat
```

### 3. 运行模式说明

| 模式 | 说明 | 适用场景 | 推送时机 |
|------|------|----------|----------|
| **daily** | 当日汇总 | 定时推送每日报告 | 定时推送当日所有匹配新闻 |
| **current** | 当前榜单 | 高频监控最新热点 | 定时推送当前榜单匹配新闻 |
| **incremental** | 增量监控 | 实时监控新增热点 | 仅在有新增内容时推送 |

## API 接口文档

### AI 对话接口

```bash
# 创建新会话
POST /api/v1/chat/sessions
{
  "inject_context": true,
  "platforms": ["zhihu", "weibo"],
  "news_limit": 50
}

# 获取会话信息
GET /api/v1/chat/sessions/{session_id}

# 发送消息
POST /api/v1/chat/sessions/{session_id}/messages
{
  "message": "分析今天最热门的话题",
  "inject_context": false
}

# 流式发送消息（SSE）
POST /api/v1/chat/sessions/{session_id}/messages/stream

# 列出所有会话
GET /api/v1/chat/sessions?limit=100

# 删除会话
DELETE /api/v1/chat/sessions/{session_id}
```

### 系统管理接口

```bash
# 获取系统状态
GET /api/v1/system/status

# 获取 LLM 服务状态
GET /api/v1/system/llm/status

# 手动触发爬取
POST /api/v1/system/trigger-crawl?mode=daily
```

### 仪表板数据接口

```bash
# 获取仪表板配置
GET /api/v1/dashboard/config

# 获取最新新闻数据
GET /api/v1/dashboard/latest?platforms=zhihu,weibo&limit=100
```

### 调度器管理接口

```bash
# 获取调度器状态
GET /api/v1/scheduler/status

# 获取任务执行历史
GET /api/v1/scheduler/history?limit=10

# 手动触发任务
POST /api/v1/scheduler/trigger?mode=daily

# 暂停/恢复任务
POST /api/v1/scheduler/pause
POST /api/v1/scheduler/resume
```

## 前端仪表板

**访问地址**: http://localhost:8000/

**功能特性**:
- 实时显示热点新闻
- 按平台分类查看
- 关键词筛选和搜索
- 热度趋势图表
- 响应式设计 (支持移动端)

**文件位置**: `hotspot_dashboard/index.html`

## 架构设计

### 核心设计原则

1. **单一职责原则 (SRP)**: 每个类只负责一个功能
2. **开放封闭原则 (OCP)**: 易于扩展,无需修改核心代码
3. **里氏替换原则 (LSP)**: 子类可以替换父类使用
4. **接口隔离原则 (ISP)**: 接口简洁明确
5. **依赖倒置原则 (DIP)**: 依赖抽象而非具体实现

### 工作流程

```
1. ConfigManager 加载配置 (config.yaml + 环境变量)
2. SourceRegistry 初始化信息源
3. BaseSource 子类爬取新闻数据
4. NewsFilter 关键词筛选 (普通词/必须词+/过滤词!)
5. NewsRanking 权重计算和排序 (排名60% + 频次30% + 热度10%)
6. NewsReporter 生成报告 (文本/HTML)
7. NotificationManager 多渠道推送
8. PushRecordManager 记录推送状态
```

### 插件化架构

- **信息源插件**: 继承 `BaseSource` 即可添加新数据源
- **通知器插件**: 继承 `BaseNotifier` 即可添加新通知渠道
- **自动注册**: `SourceRegistry` 和 `NotificationManager` 自动发现插件

## 配置说明

### 配置优先级

**环境变量 > config.yaml**

示例:
```bash
# 环境变量会覆盖配置文件
export FEISHU_WEBHOOK_URL="https://..."
python main.py
```

### 关键配置项

#### 信息源配置 (config/config.yaml)

```yaml
SOURCES:
  enabled:
    - newsnow      # 默认信息源
    - rss          # RSS 订阅源
    - youtube      # YouTube 热门视频
  newsnow:
    api_url: "https://newsnow.busiyi.world/api/s"
  rss:
    feeds:
      - url: "https://36kr.com/feed"
        name: "36氪"
  youtube:
    api_key: ""  # YouTube Data API v3 密钥
    regions:
      - "US"
    max_results: 20
```

#### 关键词筛选 (config/frequency_words.txt)

支持三种语法:
- **普通词**: 标题包含任一即匹配
- **必须词 (+)**: 必须同时包含
- **过滤词 (!)**: 包含则排除

示例:
```
人工智能
AI
+技术
!培训
```

#### 通知配置

```yaml
notification:
  enable_notification: true
  webhooks:
    feishu_url: ""
    dingtalk_url: ""
    wework_url: ""
    telegram_bot_token: ""
    telegram_chat_id: ""
    email_from: ""
    email_password: ""
    email_to: ""
    ntfy_server_url: "https://ntfy.sh"
    ntfy_topic: ""
```

**重要**: 敏感信息应通过环境变量传递,不要写在配置文件中!

#### AI 对话配置

```yaml
llm:
  provider: "deepseek"  # 服务商标识
  base_url: "https://api.deepseek.com/v1"
  api_key: ""  # 建议通过环境变量 LLM_API_KEY 配置
  model: "deepseek-chat"
  max_tokens: 20000
  temperature: 0.7

chat:
  storage_path: "conversations"
  max_history_length: 20
  context_news_limit: 50
```

**支持的服务商**:
- OpenAI: `base_url="https://api.openai.com/v1", model="gpt-4"`
- DeepSeek: `base_url="https://api.deepseek.com/v1", model="deepseek-chat"`
- Moonshot: `base_url="https://api.moonshot.cn/v1", model="moonshot-v1-8k"`
- Azure OpenAI: `base_url="https://{your-resource}.openai.azure.com"`
- 本地 Ollama: `base_url="http://localhost:11434/v1", model="llama3"`

#### 定时任务调度器配置

```yaml
scheduler:
  enabled: true  # 是否启用定时任务调度器
  trigger_type: "interval"  # "interval" 或 "cron"
  mode: "daily"  # 爬取模式

  # 间隔触发配置
  interval_seconds: 3600  # 每小时执行一次

  # Cron 触发配置
  cron_expression: "0 * * * *"  # 每小时整点执行
```

**Cron 表达式示例**:
- `"0 * * * *"` - 每小时整点执行
- `"0 */2 * * *"` - 每 2 小时执行
- `"0 9,12,18,21 * * *"` - 每天 9:00、12:00、18:00、21:00 执行
- `"*/30 * * * *"` - 每 30 分钟执行

## 扩展开发

### 添加新的信息源

1. 创建新类继承 `BaseSource`
2. 实现必需方法: `source_id`, `source_name`, `fetch_news()`
3. 放在 `src/sources/` 目录下,自动注册

示例:
```python
from src.sources.base import BaseSource
from src.models.news import News
from typing import List

class MySource(BaseSource):
    @property
    def source_id(self) -> str:
        return "my_source"

    @property
    def source_name(self) -> str:
        return "我的信息源"

    def fetch_news(self, **kwargs) -> List[News]:
        news_list = []
        # ... 实现爬取逻辑 ...
        return news_list
```

### 添加新的通知渠道

1. 创建新类继承 `BaseNotifier`
2. 实现必需方法: `name`, `is_configured()`, `send()`
3. 放在 `src/notifiers/` 目录下,在 `NotificationManager` 中注册

示例:
```python
from src.notifiers.base import BaseNotifier

class MyNotifier(BaseNotifier):
    @property
    def name(self) -> str:
        return "我的通知渠道"

    def is_configured(self) -> bool:
        return bool(self.config.get("MY_WEBHOOK_URL"))

    def send(self, report_data, report_type, **kwargs) -> bool:
        # ... 实现发送逻辑 ...
        return True
```

## 测试

项目包含 **87+ 单元测试用例**:

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_core/ -v
pytest tests/test_sources/ -v
pytest tests/test_notifiers/ -v
pytest tests/test_api/ -v

# 查看测试覆盖率
pytest tests/ --cov=src --cov-report=html
```

## 部署方式

### 1. GitHub Actions（自动化）

- Fork 项目到你的 GitHub 账户
- 在 Settings → Secrets 中配置 webhook URLs
- 每小时自动执行（可修改 `.github/workflows/crawler.yml`）

### 2. Docker 部署

```bash
# 进入 docker 目录
cd docker

# 启动服务
docker-compose up -d

# 查看日志
docker logs -f trend-radar

# 服务管理
docker exec -it trend-radar python manage.py status
docker exec -it trend-radar python manage.py run
```

### 3. 本地运行

```bash
# 安装依赖（首次运行）
pip install -r requirements.txt

# 运行爬虫
python main.py

# 或启动 API 服务
./start_api.sh
```

## 常见问题

### Q: 如何回退到原版本?
A: 直接运行 `python main_legacy.py` 即可。

### Q: 如何访问前端页面?
A: 启动 API 服务后,访问 http://localhost:8000/

### Q: 如何更改 API 服务端口?
A: 修改 `src/api/server.py` 中的端口号,或通过环境变量 `PORT` 设置。

### Q: 如何配置 AI 对话功能?
A: 在 `config.yaml` 中配置 `llm` 部分,或通过环境变量 `LLM_API_KEY` 设置 API 密钥。

### Q: 定时任务不执行怎么办?
A: 检查 `config.yaml` 中 `scheduler.enabled` 是否为 `true`,查看日志确认调度器是否正常启动。

### Q: 新版本性能如何?
A: 模块化设计对性能影响极小,核心算法保持一致。

### Q: 如何调试问题?
A: 每个模块都有详细的日志输出,可以追踪完整流程。

## 重构亮点

### 代码质量提升

| 指标 | 原版本 | 重构版本 | 改进 |
|------|--------|----------|------|
| 文件数量 | 1个 | 40+ 个 | 模块化 |
| 最大文件行数 | 4000+ | ~400 | -90% |
| 测试覆盖 | 0% | 87 个测试 | +100% |
| 可扩展性 | 低 | 高 | 插件化 |

### 兼容性

✅ **配置文件**: 完全兼容原版 config.yaml
✅ **输出格式**: 文本报告格式与原版一致
✅ **推送逻辑**: 保留所有推送控制功能
✅ **数据格式**: 输出目录结构与原版相同

### 新增功能

✅ **API 服务**: 提供完整的 RESTful API
✅ **AI 对话**: 基于大模型的智能分析
✅ **可视化仪表板**: 热点雷达前端界面
✅ **YouTube 监控**: 热门视频信息源
✅ **定时调度器**: 内置任务调度功能

## 技术栈

- **Python**: 3.10+
- **Web 框架**: FastAPI (API 服务)
- **任务调度**: APScheduler
- **HTTP 请求**: requests
- **配置管理**: PyYAML
- **时区处理**: pytz
- **RSS 解析**: feedparser
- **大模型对接**: OpenAI API 兼容接口
- **测试框架**: pytest

## 许可证

GPL-3.0 License
