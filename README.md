# Avalon_Alone

阿瓦隆游戏 AI 版本：一个支持 AI 玩家的阿瓦隆游戏实现。

## 项目简介

这是一个基于 FastAPI 和现代 Web 技术的阿瓦隆游戏实现，支持：
- 5-10 名玩家游戏
- AI 玩家支持（可配置不同 AI 引擎）
- 实时 WebSocket 通信
- 完整的游戏流程控制
- 现代化的 Web 界面

## 功能特性

### 游戏功能
- ✅ 完整的阿瓦隆游戏规则实现
- ✅ 支持所有标准角色（梅林、派西维尔、忠臣、莫甘娜、刺客、奥伯伦、莫德雷德、爪牙）
- ✅ 5-10 人游戏配置
- ✅ 任务进度跟踪
- ✅ 队伍投票和任务投票
- ✅ 刺杀阶段
- ✅ 游戏结果判定

### 技术特性
- ✅ FastAPI 后端 API
- ✅ WebSocket 实时通信
- ✅ 现代化响应式前端界面
- ✅ AI 玩家支持
- ✅ 完整的错误处理
- ✅ API 文档自动生成

## 目录结构

```
Avalon_Alone/
├── backend/                 # 后端代码
│   ├── __init__.py         # 后端包入口
│   ├── constants.py        # 游戏常量定义
│   ├── game.py             # 游戏流程控制主类
│   ├── player.py           # 玩家、AI 玩家、上帝角色类
│   └── api.py              # FastAPI 接口
├── frontend/               # 前端代码
│   ├── index.html          # 主页面
│   ├── styles.css          # 样式文件
│   └── script.js           # JavaScript 逻辑
├── requirements.txt        # Python 依赖
├── start_server.py         # 服务器启动脚本
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