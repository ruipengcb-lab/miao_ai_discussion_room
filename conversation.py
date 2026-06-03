from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


DEFAULT_USER_NAME = "喵酱"
DEFAULT_PARTICIPANTS = ["ChatGPT", "DeepSeek", "GLM", "MiniMax"]
DEFAULT_PARTICIPANT_URLS = {
    "ChatGPT": "https://chatgpt.com/",
    "DeepSeek": "https://chat.deepseek.com/",
    "GLM": "https://chatglm.cn/",
    "MiniMax": "https://agent.minimaxi.com/",
}
OLD_DEFAULT_PARTICIPANTS = ["ChatGPT", "Claude", "Gemini"]


# 单条发言的数据结构。后续接真实 API 时，也可以在 metadata 里记录模型名、token、耗时等信息。
@dataclass
class Message:
    speaker: str
    role: str
    content: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "speaker": self.speaker,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
        }

    def matches(self, other: "Message") -> bool:
        return (
            self.speaker == other.speaker
            and self.role == other.role
            and self.content == other.content
            and self.created_at == other.created_at
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        speaker = str(data.get("speaker", "未知发言者"))
        if speaker == "用户":
            speaker = DEFAULT_USER_NAME

        return cls(
            speaker=speaker,
            role=str(data.get("role", "ai")),
            content=str(data.get("content", "")),
            created_at=str(data.get("created_at", datetime.now().isoformat(timespec="seconds"))),
        )


class Conversation:
    """统一管理讨论历史，UI 和 prompt 生成器都只从这里取数据。"""

    def __init__(
        self,
        title: str = "",
        participants: list[str] | None = None,
        participant_urls: dict[str, str] | None = None,
        messages: list[Message] | None = None,
        conversation_id: str | None = None,
        updated_at: str | None = None,
        user_name: str = DEFAULT_USER_NAME,
    ) -> None:
        self.conversation_id = conversation_id or str(uuid4())
        self.title = title
        self.user_name = user_name.strip() or DEFAULT_USER_NAME
        self.participants = participants or DEFAULT_PARTICIPANTS.copy()
        self.participant_urls = participant_urls or {}
        for name in self.participants:
            self.participant_urls.setdefault(name, DEFAULT_PARTICIPANT_URLS.get(name, ""))
        self.messages = messages or []
        self.updated_at = updated_at or datetime.now().isoformat(timespec="seconds")

    def add_user_message(self, content: str, speaker: str | None = None) -> Message:
        return self.add_message(speaker=speaker or self.user_name, role="user", content=content)

    def add_ai_message(self, speaker: str, content: str) -> Message:
        return self.add_message(speaker=speaker, role="ai", content=clean_ai_reply(content))

    def add_message(self, speaker: str, role: str, content: str) -> Message:
        message = Message(speaker=speaker.strip() or "未知发言者", role=role, content=content.strip())
        self.messages.append(message)
        self.touch()
        return message

    def clear(self) -> None:
        self.messages.clear()
        self.touch()

    def delete_message(self, index: int) -> bool:
        if 0 <= index < len(self.messages):
            self.messages.pop(index)
            self.touch()
            return True
        return False

    def message_index(self, message: Message) -> int:
        for i, m in enumerate(self.messages):
            if m.matches(message):
                return i
        return -1

    def set_title(self, title: str) -> None:
        self.title = title.strip()
        self.touch()

    def set_participants(self, participants: list[str]) -> None:
        cleaned = [name.strip() for name in participants if name.strip()]
        self.participants = cleaned or DEFAULT_PARTICIPANTS.copy()
        self.participant_urls = {
            name: self.participant_urls.get(name) or DEFAULT_PARTICIPANT_URLS.get(name, "")
            for name in self.participants
        }
        self.touch()

    def set_participant_url(self, name: str, url: str) -> None:
        if name in self.participants:
            self.participant_urls[name] = url.strip()
            self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.now().isoformat(timespec="seconds")

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "user_name": self.user_name,
            "participants": self.participants,
            "participant_urls": self.participant_urls,
            "messages": [message.to_dict() for message in self.messages],
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Conversation":
        participants = list(data.get("participants") or DEFAULT_PARTICIPANTS.copy())
        # 兼容旧版本里把“喵酱”放进 AI 参与者列表的保存文件。
        participants = [name for name in participants if name not in {DEFAULT_USER_NAME, "总结"}]
        if participants == OLD_DEFAULT_PARTICIPANTS:
            participants = DEFAULT_PARTICIPANTS.copy()
        for item in data.get("messages", []):
            speaker = str(item.get("speaker", ""))
            role = str(item.get("role", ""))
            if role == "ai" and speaker and speaker != "总结" and speaker not in participants:
                participants.append(speaker)
        participants = [name for name in DEFAULT_PARTICIPANTS if name in participants] + [
            name for name in participants if name not in DEFAULT_PARTICIPANTS
        ]

        return cls(
            conversation_id=str(data.get("conversation_id") or uuid4()),
            title=str(data.get("title", "")),
            user_name=DEFAULT_USER_NAME,
            participants=participants or DEFAULT_PARTICIPANTS.copy(),
            participant_urls=dict(data.get("participant_urls") or {}),
            messages=[Message.from_dict(item) for item in data.get("messages", [])],
            updated_at=str(data.get("updated_at", datetime.now().isoformat(timespec="seconds"))),
        )


def clean_ai_reply(content: str) -> str:
    """清理从网页复制回来时夹带的资料来源定义行和常见网页开场废话。"""
    cleaned_lines: list[str] = []
    source_line_pattern = re.compile(r"^\s*\[\d+\]:\s+https?://\S+.*$")

    for line in content.splitlines():
        if source_line_pattern.match(line):
            continue
        cleaned_lines.append(_normalize_inline_heading(line))

    return _strip_leading_boilerplate("\n".join(cleaned_lines)).strip()


def _normalize_inline_heading(line: str) -> str:
    """避免网页 markdown 标题在 history 里显示得过大，同时给无换行的编号标题补换行。"""
    line = re.sub(r"^\s{0,3}#{1,6}\s+", "", line)
    line = re.sub(r"(?<!^)(?=\d+\.\s*[\u4e00-\u9fffA-Za-z])", "\n", line)
    line = re.sub(r"(?<!^)(?=\*\*\d+\.\s*)", "\n", line)
    return line


def _strip_leading_boilerplate(content: str) -> str:
    lines = content.splitlines()
    boilerplate_patterns = [
        re.compile(r"^\s*好的[，,]\s*我已收到你的请求[，,]\s*正在处理中[。.]?\s*$"),
        re.compile(r"^\s*Let me first read the file you['’]ve shared.*$", re.IGNORECASE),
    ]

    while lines:
        first = lines[0]
        if not first.strip():
            lines.pop(0)
            continue
        if any(pattern.match(first) for pattern in boilerplate_patterns):
            lines.pop(0)
            continue
        break

    while lines and not lines[0].strip():
        lines.pop(0)

    return "\n".join(lines)
