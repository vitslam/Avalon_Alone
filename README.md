# Avalon_Alone

阿瓦隆游戏 AI 版本：一个支持 AI 玩家的阿瓦隆游戏实现。

## 项目简介

这是一个基于 FastAPI 和现代 Web 技术的阿瓦隆游戏实现，支持：
- 5-10 名玩家游戏
- AI 玩家支持（可配置不同 AI 引擎）
- 实时 WebSocket 通信
- 完整的游戏流程控制
- 现代化的 Web 界面
- AI 请求日志记录

## 功能特性

### 游戏功能
- ✅ 完整的阿瓦隆游戏规则实现
- ✅ 支持所有标准角色（梅林、派西维尔、忠臣、莫甘娜、刺客、奥伯伦、莫德雷德、爪牙）
- ✅ 5-10 人游戏配置
- ✅ 任务进度跟踪
- ✅ 队伍投票和任务投票
- ✅ 刺杀阶段
- ✅ 游戏结果判定

### AI 功能
- ✅ 支持多种 AI 引擎（GPT-3.5、GPT-4、Claude、GLM-4.5-Flash）
- ✅ 可配置的 AI 模型选择
- ✅ AI 请求日志记录（JSONL 格式）
- ✅ 环境变量配置管理
- ✅ AI 玩家智能决策

### 技术特性
- ✅ FastAPI 后端 API
- ✅ WebSocket 实时通信
- ✅ 现代化响应式前端界面
- ✅ AI 玩家支持
- ✅ 完整的错误处理
- ✅ API 文档自动生成
- ✅ 详细的 AI 请求日志
- ✅ 服务执行状态日志
- ✅ 超时控制和错误恢复
- ✅ 内存使用监控

## 配置说明

### 环境变量配置

项目使用 `.env` 文件进行配置，请复制 `env.example` 为 `.env` 并根据需要修改：

```bash
# AI提供商配置
AI_PROVIDER=zhipu          # 可选: zhipu, openai, anthropic
AI_MODEL=glm-4.5-flash     # 模型名称
AI_RESPONSE_TIMEOUT=30     # 请求超时时间（秒）
AI_FALLBACK_ENABLED=true   # 是否启用备用逻辑

# API密钥配置（至少配置一个）
ZHIPU_API_KEY=your_zhipu_api_key_here      # 智谱AI API密钥
OPENAI_API_KEY=your_openai_api_key_here     # OpenAI API密钥
ANTHROPIC_API_KEY=your_anthropic_api_key_here # Anthropic API密钥

# 服务器配置
AVALON_HOST=0.0.0.0
AVALON_PORT=8000
AVALON_DEBUG=true
AVALON_RELOAD=true

# 日志配置
AVALON_LOG_LEVEL=INFO
AVALON_LOG_FILE=avalon.log
AVALON_AI_LOG_ENABLED=true
AVALON_AI_LOG_DIR=ai_logs
```

### 日志文件说明

#### AI请求日志 (`ai_logs/`)
- 每场游戏一个文件：`game_YYYYMMDD_HHMMSS.jsonl`
- 记录所有AI请求的详细信息
- 包含模型名称、请求类型、玩家ID、响应内容、耗时等

#### 服务执行日志 (`logs/`)
- 每日一个文件：`service_YYYYMMDD.log`
- 记录服务器执行状态和请求处理情况
- 包含API请求、AI请求、游戏状态变化、错误信息等

### 监控和调试

#### 健康检查
```bash
curl http://localhost:8000/health
```

#### 服务监控
```bash
python monitor_service.py
```

#### 查看最新日志
```bash
# 查看最新服务日志
tail -f logs/service_$(date +%Y%m%d).log

# 查看最新AI日志
ls -la ai_logs/ | tail -1
tail -f ai_logs/game_$(ls ai_logs/ | tail -1)
```

#### 内存监控
健康检查端点会返回内存使用情况，如果内存使用过高可能导致卡死。

### 卡死问题排查

如果游戏卡死，可以通过以下方式排查：

1. **检查服务日志**：
   ```bash
   tail -f logs/service_$(date +%Y%m%d).log
   ```

2. **检查AI请求日志**：
   ```bash
   tail -f ai_logs/game_*.jsonl
   ```

3. **检查健康状态**：
   ```bash
   curl http://localhost:8000/health
   ```

4. **强制重启服务**：
   ```bash
   lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
   python start_server.py
   ```

### 常见问题

#### 1. AI请求超时
- 检查网络连接
- 确认API密钥有效
- 调整 `AI_RESPONSE_TIMEOUT` 参数

#### 2. 内存使用过高
- 检查是否有内存泄漏
- 重启服务释放内存
- 监控内存使用趋势

#### 3. WebSocket连接断开
- 检查前端连接状态
- 查看服务日志中的WebSocket事件
- 重新连接前端

### 支持的AI引擎

| 引擎ID | 名称 | 提供商 | 模型 | 描述 |
|--------|------|--------|------|------|
| `gpt-3.5` | GPT-3.5 | OpenAI | gpt-3.5-turbo | OpenAI GPT-3.5 模型 |
| `gpt-4` | GPT-4 | OpenAI | gpt-4 | OpenAI GPT-4 模型 |
| `claude` | Claude | Anthropic | claude-3-sonnet-20240229 | Anthropic Claude 模型 |
| `glm-4.5-flash` | GLM-4.5-Flash | 智谱AI | glm-4.5-flash | 智谱AI GLM-4.5-Flash 模型 |

### AI 日志记录

系统会自动记录所有 AI 请求到 JSONL 格式的日志文件中，包含以下信息：
- 时间戳
- 模型名称
- 请求类型（发言、队伍选择、投票、刺杀）
- 玩家ID
- 系统提示和用户提示
- 模型回复
- 请求耗时
- 错误信息（如果有）

## 目录结构

```
Avalon_Alone/
├── backend/                 # 后端代码
│   ├── __init__.py         # 后端包入口
│   ├── constants.py        # 游戏常量定义
│   ├── game.py             # 游戏流程控制主类
│   ├── player.py           # 玩家、AI 玩家、上帝角色类
│   ├── ai_service.py       # AI 服务
│   ├── ai_controller.py    # AI 控制器
│   ├── ai_logger.py        # AI 日志记录器
│   └── api.py              # FastAPI 接口
├── frontend/               # 前端代码
│   ├── index.html          # 主页面
│   ├── styles.css          # 样式文件
│   └── script.js           # JavaScript 逻辑
├── config.py               # 配置文件
├── requirements.txt        # Python 依赖
├── start_server.py         # 服务器启动脚本
├── env.example            # 环境变量示例
└── README.md              # 项目说明
```

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务器

```bash
python start_server.py
```

或者直接使用 uvicorn：

```bash
uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

### 3. 访问应用

- **API 文档**: http://localhost:8000/docs
- **前端界面**: 打开 `frontend/index.html` 文件
- **健康检查**: http://localhost:8000/health

## 游戏规则

### 角色分配
- **好人阵营**: 梅林、派西维尔、忠臣
- **坏人阵营**: 莫甘娜、刺客、奥伯伦、莫德雷德、爪牙

### 特殊能力
- **梅林**: 能看到除了莫德雷德之外的所有坏人
- **派西维尔**: 能看到梅林和莫甘娜
- **坏人**: 能看到其他坏人（除了奥伯伦）

### 游戏流程
1. **角色分配**: 上帝分配角色并发送秘密信息
2. **队伍选择**: 队长选择任务队伍
3. **队伍投票**: 所有玩家对队伍进行投票
4. **任务投票**: 队伍成员进行任务投票
5. **结果判定**: 根据任务结果判定胜负
6. **刺杀阶段**: 如果好人获胜，刺客可以刺杀梅林

## API 接口

### 游戏管理
- `POST /game/start` - 开始新游戏
- `GET /game/state` - 获取游戏状态
- `POST /game/reset` - 重置游戏

### 游戏操作
- `POST /game/select-team` - 选择任务队伍
- `POST /game/vote-team` - 队伍投票
- `POST /game/vote-mission` - 任务投票
- `POST /game/assassinate` - 刺客刺杀

### 信息查询
- `GET /game/roles` - 获取角色信息
- `GET /game/phases` - 获取游戏阶段
- `GET /game/mission-config` - 获取任务配置
- `GET /game/available-players` - 获取可用玩家

### WebSocket
- `WS /ws` - 实时游戏状态更新

## 前端功能

### 游戏设置
- 添加/删除玩家
- 配置 AI 玩家
- 选择 AI 引擎

### 游戏界面
- 实时游戏状态显示
- 任务进度看板
- 玩家角色卡片
- 队伍选择界面
- 投票界面
- 聊天系统

### 响应式设计
- 支持桌面和移动设备
- 现代化 UI 设计
- 流畅的动画效果

## 开发说明

### 后端架构
- **AvalonGame**: 游戏主控制器，管理游戏流程
- **Player/AIPlayer**: 玩家类，支持 AI 决策
- **God**: 上帝角色，负责角色分配和信息传递
- **API**: RESTful API 和 WebSocket 接口

### 前端架构
- **HTML**: 语义化结构
- **CSS**: 现代化样式，支持响应式
- **JavaScript**: 模块化设计，实时通信

### 扩展性
- 支持添加新的 AI 引擎
- 可扩展游戏规则
- 支持自定义角色
- 可添加更多游戏模式

## 技术栈

### 后端
- **FastAPI**: 现代 Python Web 框架
- **Pydantic**: 数据验证
- **WebSocket**: 实时通信
- **Uvicorn**: ASGI 服务器

### 前端
- **HTML5**: 语义化标记
- **CSS3**: 现代化样式
- **JavaScript ES6+**: 现代 JavaScript
- **WebSocket**: 实时通信

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。

---

**享受阿瓦隆游戏的乐趣！** 🎮