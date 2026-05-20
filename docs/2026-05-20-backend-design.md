# 小菜桌宠后端设计

## 概述
为小菜桌宠实现 Flask 后端，接收前端聊天请求，调用 DeepSeek API 生成带个性的 AI 回复，并维护对话记忆和宠物状态持久化。

## 架构

```
pet.js (fetch POST /chat) → Flask (5000) → DeepSeek API (OpenAI 兼容)
                              ↕
                         memory.json (个性/好感度)
                         memory dict (对话历史，最近10轮)
```

## API

### `POST /chat`

**请求：**
```json
{ "message": "你好" }
```

**响应：**
```json
{
  "reply": "哼，你还知道来找我？",
  "emotion": "talking"
}
```

**错误响应：**
```json
{
  "reply": "我好像断网了…",
  "emotion": "idle"
}
```

## 核心设计

### System Prompt 构造
从 `memory.json` 读取 `personality` 和 `username`，构造 system prompt：
- 个性设定：嘴毒但关心人
- 要求回复以 `[emotion:xxx]` 前缀标记情绪（happy/talking/idle/angry）
- 控制回复长度在 50 字以内

### 对话记忆
- 内存中维护 `conversations` 字典（key: "default"）
- 每次请求追加 user/assistant 消息
- 保留最近 10 轮（20 条消息），超出则截断
- 重启后历史丢失（当前阶段可接受）

### 情绪解析
- 从 LLM 回复中提取 `[emotion:xxx]` 前缀
- 不匹配时默认 `talking`
- 支持：happy / talking / idle / angry

### 好感度系统
- 每次成功对话 `favor += 1`
- 写入 `memory.json` 持久化
- 好感度影响宠物回复语气（通过 system prompt 注入）

### 状态管理
- 加载 `memory.json` 获取 personality / favor / mood / energy
- `/chat` 请求时注入到 system prompt
- 回复成功后递增 favor 并持久化

## 文件

| 文件 | 说明 |
|------|------|
| `backend/app.py` | Flask 主程序，路由 + DeepSeek 调用 |
| `backend/.env` | 环境变量（从 .env.example 创建） |
| `backend/config.json` | 后端配置（已有） |
| `backend/memory.json` | 宠物记忆持久化（已有，新增 favor 递增） |
| `backend/requirements.txt` | 依赖（已有） |

## 错误处理
- DeepSeek API 调用失败 → 返回固定兜底回复
- 请求格式错误 → 400 + 错误提示
- 内存未初始化 → 优雅降级返回默认回复
