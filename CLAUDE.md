# xiaocai-pet 项目规范

## 项目概述
AI 语音陪伴型桌面宠物（Electron + Flask + DeepSeek）

## 技术栈
- 桌面壳：Electron 33（无框透明窗口）
- 前端：原生 HTML + CSS + Vanilla JS（无框架）
- 宠物形象：手绘 SVG（CSS 控制表情切换）
- 后端：Flask 3.1（Python）
- AI：DeepSeek API（deepseek-chat）

## 项目结构
```
xiaocai-pet/
├── package.json              # Electron 配置
├── 启动桌宠.bat              # 一键启动（后端 + 前端）
├── 开发文档.md               # 项目开发文档（所有进度记录在此）
├── electron/
│   ├── main.js               # Electron 主进程
│   └── preload.js            # 预加载脚本
├── frontend/
│   ├── index.html            # 主界面
│   ├── pet.js                # 前端逻辑（状态机、拖拽、聊天、番茄钟）
│   ├── style.css             # 样式 & CSS 动画
│   └── assets/pet.svg        # 宠物 SVG
├── backend/
│   ├── app.py                # Flask 主程序
│   ├── config.json           # 后端配置
│   ├── .env                  # API Key（勿提交）
│   ├── requirements.txt      # Python 依赖
│   ├── memory.json           # 宠物状态（好感度/心情/精力）
│   ├── conversations_short.json  # 短期记忆（最近 15 轮）
│   └── conversations_long.json   # 长期记忆（自动归档摘要）
└── docs/
    └── *.md                  # 设计文档
```

## 开发规范

### 文档
- 所有开发进度、变更记录只写到 `开发文档.md`，不另建其他文档
- 每次修改先读 `开发文档.md` 了解当前状态
- 重要变更需更新开发日志章节

### 代码风格
- 前端：纯原生 JS，不引入框架
- 后端：单文件 `app.py`，功能复杂后再拆分
- 注释：只写 WHY，不写 WHAT（好命名 > 注释）
- 配置：敏感信息放 `.env`，不上传 git

### 对话记忆
- 短期记忆 `conversations_short.json`：最近 15 轮，文件持久化
- 长期记忆 `conversations_long.json`：超出自动归档摘要
- 记忆持久化到文件，不依赖内存

### 界面
- Electron 窗口 280×480px
- 透明背景，始终置顶
- 气泡自适应高度，SVG 可压缩让位

### 启动方式
- 双击 `启动桌宠.bat`：自动启动后端 + 打开窗口
- 开发时：`cd backend && python app.py` 开后端，再 `npm start` 开前端

### 沟通语言
- 与用户交流使用中文
- 命名优先使用英文
