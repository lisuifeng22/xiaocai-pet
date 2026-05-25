# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).parent
MEMORY_PATH = BASE_DIR / "memory.json"
SHORT_MEM_PATH = BASE_DIR / "conversations_short.json"
LONG_MEM_PATH = BASE_DIR / "conversations_long.json"

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash")

SHORT_MAX_ROUNDS = 15
ARCHIVE_BATCH = 5

# ===========================
# 全局状态 & 主动推送
# ===========================
clients = set()
last_interaction = datetime.now()
triggered_today = set()

scheduled_events = [
    {"hour": 8,  "minute": 0, "msg": "早上好，今天也要努力哦~"},
    {"hour": 12, "minute": 0, "msg": "中午啦，吃饭了吗？"},
    {"hour": 21, "minute": 0, "msg": "晚安时间到了，该休息啦~"},
]

INACTIVITY_THRESHOLD = 3600
CHECK_INTERVAL = 30


def send_message_to_frontend(msg):
    print(f"[主动提醒发送] {msg}")


def proactive_loop():
    global triggered_today, last_interaction
    while True:
        now = datetime.now()
        today_key = now.date()

        if not hasattr(proactive_loop, "current_date") or proactive_loop.current_date != today_key:
            triggered_today = set()
            proactive_loop.current_date = today_key

        for event in scheduled_events:
            event_id = f"{today_key}-{event['hour']}-{event['minute']}"
            if event_id not in triggered_today:
                if now.hour == event["hour"] and now.minute == event["minute"]:
                    send_message_to_frontend(event["msg"])
                    triggered_today.add(event_id)

        if (datetime.now() - last_interaction).seconds > INACTIVITY_THRESHOLD:
            send_message_to_frontend("哼，把我晾这儿好久了~")
            last_interaction = datetime.now()

        time.sleep(CHECK_INTERVAL)


threading.Thread(target=proactive_loop, daemon=True).start()


# ===========================
# 文件读写
# ===========================
def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ===========================
# 长期记忆
# ===========================
def load_long_term() -> list[dict]:
    return load_json(LONG_MEM_PATH, [])


def save_long_term(memories: list[dict]):
    save_json(LONG_MEM_PATH, memories)


def build_long_term_prompt(memories: list[dict]) -> str:
    if not memories:
        return ""
    lines = ["\n【小菜的长期记忆】"]
    for m in memories[-5:]:
        lines.append(f"- {m.get('summary', '')}")
    return "\n".join(lines)


def summarize_and_archive(history: list[dict]):
    archive_msgs = history[: ARCHIVE_BATCH * 2]
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
        return

    memories = load_long_term()
    memories.append({
        "time": datetime.now().strftime("%m-%d %H:%M"),
        "summary": summary,
    })
    save_long_term(memories)


# ===========================
# 短期记忆
# ===========================
def load_short_term() -> list[dict]:
    return load_json(SHORT_MEM_PATH, [])


def save_short_term(history: list[dict]):
    save_json(SHORT_MEM_PATH, history)


def append_short_term(user_msg: str, reply: str):
    history = load_short_term()
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": reply})

    while len(history) > SHORT_MAX_ROUNDS * 2:
        batch = history[: ARCHIVE_BATCH * 2]
        summarize_and_archive(batch)
        history = history[ARCHIVE_BATCH * 2:]

    save_short_term(history)
    return history


# ===========================
# 宠物状态 & System Prompt
# ===========================
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
        "2. 适当使用 emoji 表达情绪，让回复更生动（如 😏 😡 🥺 ✨ 🎉 💤 🤔 💪 👀 ❤️）\n"
        "3. **回复必须以 [emotion:xxx] 开头**，标记当前情绪\n"
        "4. 示例：[emotion:talking] 哼，你还知道来找我？😏"
    )

    long_memories = load_long_term()
    mem_text = build_long_term_prompt(long_memories)
    if mem_text:
        prompt += mem_text

    now = datetime.now()
    time_str = now.strftime("%Y年%m月%d日（%A） %H:%M")
    prompt += f"\n当前时间：{time_str}"

    return prompt


def parse_emotion(text: str) -> str:
    m = re.match(r"^\[emotion:([^\]]+)\]", text)
    if m:
        emotion = m.group(1).strip()
        return emotion if emotion else "talking"
    return "talking"


def strip_emotion_prefix(text: str) -> str:
    return re.sub(r"\[emotion:[^\]]+\]\s*", "", text).strip()


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


# ===========================
# HTTP Routes
# ===========================
@app.route("/focus_done", methods=["POST"])
def focus_done():
    global last_interaction
    last_interaction = datetime.now()
    send_message_to_frontend("完成 25 分钟专注啦，好棒~")
    return {"status": "ok"}


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

    append_short_term(user_msg, reply)

    emotion = parse_emotion(reply)
    clean_reply = strip_emotion_prefix(reply)

    memory["favor"] = memory.get("favor", 0) + 1
    save_memory(memory)

    return jsonify({"reply": clean_reply, "emotion": emotion})


@app.route("/history", methods=["GET"])
def get_history():
    short_term = load_short_term()
    long_term = load_long_term()

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


# ===========================
# 启动
# ===========================
if __name__ == "__main__":
    port = 5000
    print(f"小菜后端启动 → http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
