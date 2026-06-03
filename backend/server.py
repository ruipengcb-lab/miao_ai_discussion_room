import sys
import os

if getattr(sys, 'frozen', False):
    class _DummyStream:
        def write(self, s): pass
        def flush(self): pass
        def isatty(self): return False
    if sys.stderr is None:
        sys.stderr = _DummyStream()
    if sys.stdout is None:
        sys.stdout = _DummyStream()
        
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from urllib.parse import urlparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conversation import Conversation, DEFAULT_PARTICIPANT_URLS
from prompt_builder import build_prompt, build_summary_prompt, normalize_prompt_profiles
from storage import (
    archive_conversation,
    delete_archived_conversation,
    list_archived_conversations,
    load_archived_conversation,
    load_settings,
    save_conversation,
    save_settings,
)
import api_providers

app = FastAPI(title="喵酱 AI 讨论室 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_conversation = Conversation()
settings = load_settings()



# ===== Pydantic 模型 =====
class TopicUpdate(BaseModel):
    title: str

class UserMessage(BaseModel):
    content: str

class AIMessage(BaseModel):
    name: str
    content: str
    is_summary: bool = False

class ParticipantUpdate(BaseModel):
    name: str
    url: str = ""
    provider: str = ""
    api_key: str = ""
    model: str = ""

class RemoveParticipant(BaseModel):
    name: str

class PromptRequest(BaseModel):
    target_ai: str
    mode: str = "discussion"
    profile_id: Optional[str] = None

class AutoAIRequest(BaseModel):
    name: str
    profile_id: Optional[str] = None

class ArchiveRequest(BaseModel):
    path: str

class SettingsUpdate(BaseModel):
    key: str
    value: object


# ===== 会话 =====
@app.get("/api/conversation")
def get_conversation():
    return current_conversation.to_dict()

@app.put("/api/conversation/title")
def update_title(data: TopicUpdate):
    current_conversation.set_title(data.title)
    save_conversation(current_conversation)
    return {"status": "ok", "title": current_conversation.title}

@app.post("/api/conversation/clear")
def clear_conversation():
    current_conversation.clear()
    save_conversation(current_conversation)
    return {"status": "ok"}

@app.post("/api/conversation/new")
def new_conversation(data: TopicUpdate):
    global current_conversation
    if current_conversation.title or current_conversation.messages:
        archive_conversation(current_conversation)
    participants = current_conversation.participants.copy()
    participant_urls = current_conversation.participant_urls.copy()
    current_conversation = Conversation(title=data.title, participants=participants)
    current_conversation.participant_urls.update(participant_urls)
    save_conversation(current_conversation)
    return current_conversation.to_dict()


# ===== 消息 =====
@app.post("/api/messages/user")
def add_user_message(data: UserMessage):
    if not data.content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")
    current_conversation.add_user_message(data.content.strip())
    save_conversation(current_conversation)
    return current_conversation.to_dict()

@app.post("/api/messages/ai")
def add_ai_message(data: AIMessage):
    if not data.content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")
    if data.is_summary:
        current_conversation.add_message("总结", "summary", data.content.strip())
    else:
        current_conversation.add_ai_message(data.name, data.content.strip())
    save_conversation(current_conversation)
    return current_conversation.to_dict()

@app.delete("/api/messages/{index}")
def delete_message(index: int):
    if 0 <= index < len(current_conversation.messages):
        current_conversation.delete_message(index)
        save_conversation(current_conversation)
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="消息不存在")


# ===== 参与者 =====
@app.post("/api/participants")
def add_participant(data: ParticipantUpdate):
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="名称不能为空")
    if data.name in current_conversation.participants:
        raise HTTPException(status_code=400, detail="已存在")
    current_conversation.set_participants([*current_conversation.participants, data.name])
    if data.url:
        current_conversation.set_participant_url(data.name, data.url)
    if data.api_key:
        if "per_ai_api" not in settings:
            settings["per_ai_api"] = {}
        settings["per_ai_api"][data.name] = {
            "provider": data.provider or "deepseek",
            "api_key": data.api_key,
            "model": data.model or "",
        }
        save_settings(settings)
    save_conversation(current_conversation)
    return {"participants": current_conversation.participants}

@app.delete("/api/participants")
def remove_participant(data: RemoveParticipant):
    if len(current_conversation.participants) <= 1:
        raise HTTPException(status_code=400, detail="至少保留一个 AI")
    if data.name not in current_conversation.participants:
        raise HTTPException(status_code=404, detail="参与者不存在")
    current_conversation.set_participants([p for p in current_conversation.participants if p != data.name])
    current_conversation.participant_urls.pop(data.name, None)
    if "per_ai_api" in settings:
        settings["per_ai_api"].pop(data.name, None)
        save_settings(settings)
    save_conversation(current_conversation)
    return {"participants": current_conversation.participants}

@app.put("/api/participants/url")
def update_participant(data: ParticipantUpdate):
    if data.name not in current_conversation.participants and data.name != "总结":
        raise HTTPException(status_code=404, detail="参与者不存在")
    if data.url:
        current_conversation.set_participant_url(data.name, data.url)
    if data.api_key:
        if "per_ai_api" not in settings:
            settings["per_ai_api"] = {}
        settings["per_ai_api"][data.name] = {
            "provider": data.provider or "deepseek",
            "api_key": data.api_key,
            "model": data.model or "",
        }
        save_settings(settings)
    save_conversation(current_conversation)
    return {"status": "ok"}

@app.get("/api/participants/url")
def get_participant_url(name: str = Query(...)):
    url = current_conversation.participant_urls.get(name, "")
    if not url and name == "总结":
        url = "https://chat.deepseek.com/"
    if not url:
        url = DEFAULT_PARTICIPANT_URLS.get(name, "")
    if url and not urlparse(url).scheme:
        url = f"https://{url}"
    return {"url": url, "valid": bool(urlparse(url).scheme and urlparse(url).netloc)}


# ===== Prompt =====
@app.post("/api/prompt")
def generate_prompt(data: PromptRequest):
    profiles, active_id = normalize_prompt_profiles(settings)
    profile = next((p for p in profiles if p["id"] == data.profile_id), None)
    if not profile:
        profile = profiles[0] if profiles else {"id": "default", "name": "默认", "prompt_matrix": [[""]], "summary": ""}

    if data.mode == "summary" or data.target_ai == "总结":
        prompt = build_summary_prompt(current_conversation, profile)
    else:
        prompt = build_prompt(current_conversation, data.target_ai, profile)

    # 自动切到下一个未发言 AI
    next_ai = _next_unspoken_ai(data.target_ai)
    return {"prompt": prompt, "next_ai": next_ai}


def _next_unspoken_ai(current_speaker: str) -> str:
    names = current_conversation.participants
    spoken = set()
    for msg in reversed(current_conversation.messages):
        if msg.role == "user":
            break
        if msg.speaker in names:
            spoken.add(msg.speaker)
    for name in names:
        if name not in spoken:
            return name
    if current_speaker in names:
        idx = names.index(current_speaker)
        return names[(idx + 1) % len(names)]
    return names[0]


# ===== 自动调用 =====
@app.post("/api/auto-call")
async def auto_call_ai(data: AutoAIRequest):
    per_ai = settings.get("per_ai_api", {})
    api_info = per_ai.get(data.name, {})
    api_key = api_info.get("api_key", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="未配置 API Key")

    profiles, active_id = normalize_prompt_profiles(settings)
    profile = next((p for p in profiles if p["id"] == data.profile_id), profiles[0] if profiles else {"id": "default", "prompt_matrix": [[""]], "summary": ""})
    prompt = build_prompt(current_conversation, data.name, profile)

    try:
        provider_key = api_info.get("provider", "deepseek")
        model = api_info.get("model") or None
        config = api_providers.build_api_config(provider_key, api_key, model)
        provider = api_providers.create_provider(config)
        content = await provider.call(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if content:
        current_conversation.add_ai_message(data.name, content)
        save_conversation(current_conversation)

    next_ai = _next_unspoken_ai(data.name)
    return {"content": content, "next_ai": next_ai}


# ===== 设置 =====
@app.get("/api/settings")
def get_settings():
    return settings

@app.put("/api/settings/update")
def update_settings(data: SettingsUpdate):
    settings[data.key] = data.value
    save_settings(settings)
    return {"status": "ok"}


# ===== 归档 =====
@app.get("/api/archives")
def get_archives():
    return list_archived_conversations()

@app.post("/api/archives/load")
def load_archive(data: ArchiveRequest):
    global current_conversation
    archive_conversation(current_conversation)
    current_conversation = load_archived_conversation(data.path)
    save_conversation(current_conversation)
    return current_conversation.to_dict()

@app.delete("/api/archives")
def delete_archive(data: ArchiveRequest):
    delete_archived_conversation(data.path)
    return {"status": "ok"}


# ===== 导出 =====
@app.get("/api/export/json")
def export_json():
    return current_conversation.to_dict()

@app.get("/api/export/markdown")
def export_markdown():
    lines = [
        f"# {current_conversation.title or '无标题'}",
        "",
        f"- 讨论 ID：{current_conversation.conversation_id}",
        f"- 更新时间：{current_conversation.updated_at}",
        f"- AI：{', '.join(current_conversation.participants)}",
        "",
        "## 对话记录",
        "",
    ]
    for msg in current_conversation.messages:
        speaker = "我" if msg.role == "user" else msg.speaker
        lines.append(f"### {speaker}（{msg.created_at}）")
        lines.append("")
        lines.append(msg.content)
        lines.append("")
    return {"content": "\n".join(lines), "filename": _download_filename("md")}

@app.get("/api/export/txt")
def export_txt():
    lines = [
        f"讨论主题：{current_conversation.title or '无标题'}",
        f"讨论 ID：{current_conversation.conversation_id}",
        f"更新时间：{current_conversation.updated_at}",
        f"参与者：{', '.join(current_conversation.participants)}",
        "",
    ]
    for msg in current_conversation.messages:
        speaker = "我" if msg.role == "user" else msg.speaker
        lines.append("---")
        lines.append("")
        lines.append(f"{speaker}（{msg.created_at}）：")
        lines.append("")
        lines.append(msg.content)
        lines.append("")
    return {"content": "\n".join(lines), "filename": _download_filename("txt")}


def _download_filename(ext: str) -> str:
    title = "".join(c for c in (current_conversation.title or "") if c not in r'\/:*?"<>|').strip()
    safe = title or "miao_ai_discussion"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe}_{ts}.{ext}"


# ===== 前端静态文件托管 =====
import os as _os
import sys as _sys

if getattr(_sys, 'frozen', False):
    _project_root = _os.path.dirname(_os.path.abspath(_sys.executable))
    _frontend_dir = _os.path.normpath(_os.path.join(_project_root, '..', 'frontend', 'build'))
else:
    _project_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    _frontend_dir = _os.path.normpath(_os.path.join(_project_root, 'frontend', 'build'))

print("[FRONTEND] path:", _frontend_dir)
print("[FRONTEND] exists:", _os.path.isdir(_frontend_dir))

if _os.path.isdir(_frontend_dir):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    app.mount("/static", StaticFiles(directory=_os.path.join(_frontend_dir, "static")), name="static")

    @app.get("/")
    async def serve_root():
        return FileResponse(_os.path.join(_frontend_dir, "index.html"))

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        return FileResponse(_os.path.join(_frontend_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)