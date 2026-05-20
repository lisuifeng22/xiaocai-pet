import json
import os
import requests
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).parent
MEMORY_PATH = BASE_DIR / "memory.json"
SHORT_MEM_PATH = BASE_DIR / "conversations_short.json"
LONG_MEM_PATH = BASE_DIR / "conversations_long.json"

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

SHORT_MAX_ROUNDS = 15  # 短期记忆上限（轮数）
ARCHIVE_BATCH = 5       # 每次归档的轮数


# ===== 文件读写 =====

def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ===== 长期记忆 =====

def load_long_term() -> list[dict]:
    return load_json(LONG_MEM_PATH, [])


def save_long_term(memories: list[dict]):
    save_json(LONG_MEM_PATH, memories)


def build_long_term_prompt(memories: list[dict]) -> str:
    """将长期记忆组装成 system prompt 的一段"""
    if not memories:
        return ""
    lines = ["\n【小菜的长期记忆】"]
    for m in memories[-5:]:  # 最多注入最近 5 条摘要
        lines.append(f"- {m.get('summary', '')}")
    return "\n".join(lines)


def summarize_and_archive(history: list[dict]):
    """取最旧的几条对话，让 LLM 总结后归档到长期记忆"""
    archive_msgs = history[: ARCHIVE_BATCH * 2]  # 取 N 轮 = N*2 条消息
    text = "\n".join(
        f"{'主人' if m['role'] == 'user' else '小菜'}: {m['content']}"
        for m in archive_msgs
    )

    prompt = (
        "以下是主人和小菜的一段对话，请用一句话总结其中提到的重要信息"
        "（如主人的喜好、提到过的事件、小菜的情绪变化等）。"
        f"如果没有值得记的内容，回复「无」。\n\n{text}"
    )

    try:
        headers = {
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 128,
            "temperature": 0.3,
        }
        resp = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        summary = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        summary = "(归档失败)"

    if summary == "无":
        return  # 没什么好记的，直接丢弃

    memories = load_long_term()
    memories.append({
        "time": __import__("datetime").datetime.now().strftime("%m-%d %H:%M"),
        "summary": summary,
    })
    save_long_term(memories)


# ===== 短期记忆 =====

def load_short_term() -> list[dict]:
    return load_json(SHORT_MEM_PATH, [])


def save_short_term(history: list[dict]):
    save_json(SHORT_MEM_PATH, history)


def append_short_term(user_msg: str, reply: str):
    history = load_short_term()
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": reply})

    # 超过上限 → 归档一批
    while len(history) > SHORT_MAX_ROUNDS * 2:
        batch = history[: ARCHIVE_BATCH * 2]
        summarize_and_archive(batch)
        history = history[ARCHIVE_BATCH * 2:]

    save_short_term(history)
    return history


# ===== 宠物状态 =====

def load_memory() -> dict:
    return load_json(MEMORY_PATH, {
        "username": "主人",
        "personality": "嘴毒但关心人",
        "favor": 0,
        "mood": 70,
        "energy": 80,
        "last_topic": "",
        "today_tasks": [],
    })


def save_memory(memory: dict):
    save_json(MEMORY_PATH, memory)


def build_system_prompt(memory: dict) -> str:
    username = memory.get("username", "主人")
    personality = memory.get("personality", "嘴毒但关心人")
    favor = memory.get("favor", 0)

    closeness = "冷淡"
    if favor > 80:
        closeness = "非常亲近"
    elif favor > 50:
        closeness = "友好"
    elif favor > 20:
        closeness = "普通"

    prompt = (
        f"你是小菜，一个桌面宠物。你的性格：{personality}。"
        f"用户是你的主人「{username}」，你和主人的关系：{closeness}（好感度{favor}）。"
        "回复要求：\n"
        "1. 口语化，生动有趣，符合性格设定\n"
        "2. **回复必须以 [emotion:xxx] 开头**，标记当前情绪\n"
        "3. 示例：[emotion:talking] 哼，你还知道来找我？"
    )

    # 注入长期记忆
    long_memories = load_long_term()
    mem_text = build_long_term_prompt(long_memories)
    if mem_text:
        prompt += mem_text

    return prompt


def parse_emotion(text: str) -> str:
    import re
    m = re.match(r"^\[emotion:([^\]]+)\]", text)
    if m:
        emotion = m.group(1).strip()
        return emotion if emotion else "talking"
    return "talking"


def strip_emotion_prefix(text: str) -> str:
    import re
    return re.sub(r"^\[emotion:[^\]]+\]\s*", "", text).strip()


def call_llm(messages: list[dict]) -> str | None:
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.9,
    }

    try:
        resp = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


# ===== Routes =====

@app.route("/chat", methods=["POST"])
def chat():
    body = request.get_json(silent=True)
    if not body or "message" not in body:
        return jsonify({"reply": "你说啥？我没听清。", "emotion": "idle"}), 400

    user_msg = body["message"].strip()
    if not user_msg:
        return jsonify({"reply": "你说啥？我没听清。", "emotion": "idle"}), 400

    memory = load_memory()
    system_prompt = build_system_prompt(memory)
    history = load_short_term()

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_msg})

    reply = call_llm(messages)

    if reply is None:
        return jsonify({"reply": "啊？我好像断网了…", "emotion": "idle"})

    # 持久化短期记忆 + 自动归档
    append_short_term(user_msg, reply)

    emotion = parse_emotion(reply)
    clean_reply = strip_emotion_prefix(reply)

    # 好感度持久化
    memory["favor"] = memory.get("favor", 0) + 1
    save_memory(memory)

    return jsonify({"reply": clean_reply, "emotion": emotion})


@app.route("/history", methods=["GET"])
def get_history():
    short_term = load_short_term()
    long_term = load_long_term()

    # 格式化短期记忆为可读文本
    readable_short = []
    for msg in short_term:
        role = "主人" if msg["role"] == "user" else "小菜"
        readable_short.append(f"[{role}] {msg['content']}")

    return jsonify({
        "short_term": readable_short,
        "long_term": long_term,
    })


@app.route("/reset", methods=["POST"])
def reset_conversation():
    save_short_term([])
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = 5000
    print(f"小菜后端启动 → http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
