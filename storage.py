from __future__ import annotations

import json
import sys
from pathlib import Path

from conversation import Conversation


# 先用本地 JSON 保存。源码运行时写到项目 data；EXE 运行时写到 EXE 旁边的 data。
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
CURRENT_FILE = DATA_DIR / "current_conversation.json"
ARCHIVE_DIR = DATA_DIR / "conversations"
SETTINGS_FILE = DATA_DIR / "settings.json"


def load_conversation() -> Conversation:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CURRENT_FILE.exists():
        return Conversation()

    try:
        data = json.loads(CURRENT_FILE.read_text(encoding="utf-8"))
        return Conversation.from_dict(data)
    except (json.JSONDecodeError, OSError, TypeError):
        # 文件损坏时不让应用启动失败，直接给一个新讨论。
        return Conversation()


def save_conversation(conversation: Conversation) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_FILE.write_text(
        json.dumps(conversation.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def archive_conversation(conversation: Conversation) -> Path:
    """把当前讨论另存一份归档，避免创建新话题时覆盖旧话题。"""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    title = _safe_filename(conversation.title) or "untitled"
    filename = f"{conversation.updated_at.replace(':', '-')}_{title}_{conversation.conversation_id[:8]}.json"
    path = ARCHIVE_DIR / filename
    path.write_text(
        json.dumps(conversation.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def list_archived_conversations() -> list[dict[str, str | int]]:
    """读取已归档话题的轻量信息，用于网页侧回看列表。"""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, str | int]] = []

    for path in sorted(ARCHIVE_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        items.append(
            {
                "path": str(path),
                "title": str(data.get("title", "")),
                "updated_at": str(data.get("updated_at", "")),
                "message_count": len(data.get("messages", [])),
            }
        )

    return items


def load_archived_conversation(path_text: str) -> Conversation:
    path = Path(path_text)
    archive_root = ARCHIVE_DIR.resolve()
    resolved = path.resolve()
    if archive_root not in resolved.parents:
        raise ValueError("只能读取归档目录里的话题。")

    data = json.loads(resolved.read_text(encoding="utf-8"))
    return Conversation.from_dict(data)


def delete_archived_conversation(path_text: str) -> None:
    path = Path(path_text)
    archive_root = ARCHIVE_DIR.resolve()
    resolved = path.resolve()
    if archive_root not in resolved.parents:
        raise ValueError("只能删除归档目录里的话题。")
    if resolved.exists():
        resolved.unlink()


def load_settings() -> dict[str, str | bool]:
    """加载设置（API key、模式等）。兼容旧版 deepseek_api_key 配置。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        return {
            "auto_mode": False,
            "per_ai_api": {},
        }
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {
            "auto_mode": False,
            "per_ai_api": {},
        }

    # 旧版迁移：把 deepseek_api_key 转成 per_ai_api
    if "per_ai_api" not in raw:
        old_key = raw.get("deepseek_api_key", "")
        raw["auto_mode"] = bool(raw.get("auto_mode", False))
        if old_key:
            raw["per_ai_api"] = {
                "DeepSeek": {
                    "provider": "deepseek",
                    "api_key": old_key,
                    "model": "",
                }
            }
        else:
            raw["per_ai_api"] = {}
        # 清理旧字段
        raw.pop("deepseek_api_key", None)
        raw.pop("default_api_key", None)
        # 立即写回新格式
        SETTINGS_FILE.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return raw


def save_settings(settings: dict[str, str | bool]) -> None:
    """保存设置。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _safe_filename(value: str) -> str:
    cleaned = "".join(char for char in value if char not in r'\/:*?"<>|').strip()
    return cleaned[:60]


def export_markdown(conversation: Conversation) -> Path:
    """导出一份适合人工阅读的 Markdown 备份。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{conversation.updated_at.replace(':', '-')}_{conversation.conversation_id[:8]}.md"
    path = DATA_DIR / filename
    lines = [
        f"# {conversation.title}",
        "",
        f"- 讨论 ID：{conversation.conversation_id}",
        f"- 更新时间：{conversation.updated_at}",
        f"- 参与者：{', '.join(conversation.participants)}",
        "",
        "## 对话记录",
        "",
    ]
    for message in conversation.messages:
        lines.extend(
            [
                f"### {message.speaker}（{message.created_at}）",
                "",
                message.content,
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
