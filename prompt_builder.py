from __future__ import annotations

from copy import deepcopy

from conversation import Conversation, Message


SEPARATOR = "<<<此AI内容结束>>>"
DEFAULT_PROMPT_PROFILE_ID = "default"
DEFAULT_PROMPT_PROFILE = {
    "id": DEFAULT_PROMPT_PROFILE_ID,
    "name": "默认模板",
    "first_round": "",
    "later_round": "",
    "round_prompts": [],
    "prompt_matrix": [[""]],
    "summary": "",
}


def normalize_prompt_profiles(settings: dict | None) -> tuple[list[dict], str]:
    raw_profiles = []
    active_id = DEFAULT_PROMPT_PROFILE_ID
    if isinstance(settings, dict):
        raw_profiles = list(settings.get("prompt_profiles") or [])
        active_id = str(settings.get("active_prompt_profile_id") or DEFAULT_PROMPT_PROFILE_ID)

    profiles = [deepcopy(DEFAULT_PROMPT_PROFILE)]
    seen = {DEFAULT_PROMPT_PROFILE_ID}
    for raw in raw_profiles:
        if not isinstance(raw, dict):
            continue
        profile = deepcopy(DEFAULT_PROMPT_PROFILE)
        if not raw.get("later_round"):
            raw = {**raw, "later_round": raw.get("second_round") or raw.get("third_round") or ""}
        if "round_prompts" not in raw:
            migrated_prompts = [raw.get("first_round", ""), raw.get("later_round", "")]
            raw = {**raw, "round_prompts": migrated_prompts}
        profile.update({key: str(value) for key, value in raw.items() if key in profile})
        if isinstance(raw.get("round_prompts"), list):
            profile["round_prompts"] = [str(value) for value in raw["round_prompts"]]
        if isinstance(raw.get("prompt_matrix"), list):
            profile["prompt_matrix"] = _normalize_prompt_matrix(raw["prompt_matrix"])
        elif profile["round_prompts"]:
            profile["prompt_matrix"] = [[value] for value in profile["round_prompts"]]
        profile_id = profile.get("id") or _safe_profile_id(profile.get("name", ""))
        profile["id"] = profile_id
        if profile_id in seen:
            continue
        seen.add(profile_id)
        profiles.append(profile)

    if active_id not in {profile["id"] for profile in profiles}:
        active_id = DEFAULT_PROMPT_PROFILE_ID
    return profiles, active_id


def build_prompt(conversation: Conversation, target_ai: str, prompt_profile: dict | None = None) -> str:
    """生成少暗示、但语境自然的手动粘贴 prompt。

    选择 target_ai 用于判断这是第一次给它发，还是它上次发言后的后续轮。
    """
    if not conversation.messages:
        return ""

    profile = _normalized_profile(prompt_profile)
    target_name = target_ai.strip()
    messages = _messages_for_target(conversation, target_name)
    user_round_number = _current_user_round_number(conversation)
    turn_number = _current_ai_turn_number(conversation, target_name)
    template = _template_for_position(profile, user_round_number, turn_number)

    rendered = _render_template(template, conversation, target_name, messages, user_round_number, turn_number)
    if rendered:
        return rendered

    prefix = _prompt_prefix(conversation, target_name)

    if not messages:
        return f"{prefix}\n\n目前还没有其他人的新发言。"

    if _has_spoken(conversation, target_name):
        return f"""{prefix}

{_format_messages(messages)}"""

    return f"""{prefix}

每个 AI 的内容结束后会有分隔标记。你不用特意加这种分隔符。

{_format_messages(messages)}"""


def build_summary_prompt(conversation: Conversation, prompt_profile: dict | None = None) -> str:
    """生成给总结 AI 的 prompt，用于汇总多方观点。"""
    messages = _messages_after_last_summary(conversation)
    if not messages:
        return ""

    profile = _normalized_profile(prompt_profile)
    rendered = _render_template(
        profile["summary"],
        conversation,
        "总结",
        messages,
        _current_user_round_number(conversation),
        _current_ai_turn_number(conversation, "总结"),
    )
    return rendered or _format_messages(messages)


def _opening_without_messages(conversation: Conversation) -> str:
    return f"我们现在跟其他 AI 一起来讨论“{_topic_text(conversation)}”这个话题。"


def _prompt_prefix(conversation: Conversation, target_ai: str) -> str:
    if _has_spoken(conversation, target_ai):
        return "上一轮你说了之后，其他人按顺序来，是这样认为的。"
    if _has_ai_messages(conversation):
        return f"关于“{_topic_text(conversation)}”，其他 AI 是这样说的。"
    return f"关于“{_topic_text(conversation)}”，我是这样说的。"


def _topic_text(conversation: Conversation) -> str:
    return conversation.title.strip() or "这个问题"


def _normalized_profile(profile: dict | None) -> dict:
    normalized = deepcopy(DEFAULT_PROMPT_PROFILE)
    if isinstance(profile, dict):
        normalized.update({key: str(value) for key, value in profile.items() if key in normalized})
        if isinstance(profile.get("round_prompts"), list):
            normalized["round_prompts"] = [str(value) for value in profile["round_prompts"]]
        if isinstance(profile.get("prompt_matrix"), list):
            normalized["prompt_matrix"] = _normalize_prompt_matrix(profile["prompt_matrix"])
    return normalized


def _normalize_prompt_matrix(value: list) -> list[list[str]]:
    matrix: list[list[str]] = []
    for row in value:
        if isinstance(row, list):
            matrix.append([str(cell) for cell in row])
        else:
            matrix.append([str(row)])
    return matrix or [[""]]


def _template_for_position(profile: dict, user_round_number: int, turn_number: int) -> str:
    matrix = profile.get("prompt_matrix") or []
    if isinstance(matrix, list) and 0 <= user_round_number - 1 < len(matrix):
        row = matrix[user_round_number - 1]
        if isinstance(row, list) and 0 <= turn_number - 1 < len(row):
            return str(row[turn_number - 1] or "")

    prompts = profile.get("round_prompts") or []
    if isinstance(prompts, list) and 0 <= turn_number - 1 < len(prompts):
        return str(prompts[turn_number - 1] or "")
    return ""


def _safe_profile_id(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")
    return cleaned or DEFAULT_PROMPT_PROFILE_ID


def _current_ai_turn_number(conversation: Conversation, target_ai: str) -> int:
    """当前用户发言之后，第几个 AI 接力发言。

    这里的“轮次”不是第几个用户问题，而是同一轮讨论里第几个 AI 将要接话：
    第一个 AI 只拿用户问题；第二个 AI 会看到第一个 AI 的回答；之后的 AI 会看到前面所有新回答。
    如果目标 AI 已经发言过，则回到旧逻辑：给它看“它上次发言之后”的新增内容。
    """
    start_index = _last_user_message_index(conversation)
    messages = conversation.messages[start_index + 1 :] if start_index >= 0 else conversation.messages
    ai_count = 0
    for message in messages:
        if message.role == "ai" and not _is_summary(message):
            ai_count += 1
            if message.speaker == target_ai:
                return ai_count + 1
    return max(1, ai_count + 1)


def _current_user_round_number(conversation: Conversation) -> int:
    count = sum(1 for message in conversation.messages if message.role == "user")
    return max(1, count)


def _latest_user_message(conversation: Conversation) -> str:
    for message in reversed(conversation.messages):
        if message.role == "user":
            return message.content
    return ""


def _render_template(
    template: str,
    conversation: Conversation,
    target_ai: str,
    messages: list[Message],
    user_round_number: int,
    turn_number: int,
) -> str:
    values = {
        "topic": _topic_text(conversation),
        "target_ai": target_ai,
        "round": str(user_round_number),
        "turn": str(turn_number),
        "messages": _format_messages(messages),
        "latest_user_message": _latest_user_message(conversation),
        "separator": SEPARATOR,
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered.strip()


def _messages_for_target(conversation: Conversation, target_ai: str) -> list[Message]:
    if _has_spoken(conversation, target_ai):
        messages = _messages_after_last_speaker(conversation, target_ai)
    else:
        messages = _round_messages_for_first_prompt(conversation, target_ai)

    filtered = [
        message
        for message in messages
        if (message.role == "user" or message.speaker != target_ai) and not _is_summary(message)
    ]

    return filtered


def _messages_after_last_speaker(conversation: Conversation, speaker: str) -> list[Message]:
    last_index = -1
    for index, message in enumerate(conversation.messages):
        if message.speaker == speaker:
            last_index = index
    return conversation.messages[last_index + 1 :]


def _messages_after_last_summary(conversation: Conversation) -> list[Message]:
    last_index = -1
    for index, message in enumerate(conversation.messages):
        if _is_summary(message):
            last_index = index
    return [
        message
        for message in conversation.messages[last_index + 1 :]
        if not _is_summary(message)
    ]


def _round_messages_for_first_prompt(conversation: Conversation, target_ai: str) -> list[Message]:
    start_index = _last_user_message_index(conversation)
    messages = conversation.messages[start_index:] if start_index >= 0 else conversation.messages[-6:]
    # 第一次给某个 AI 发时，带上本轮里“我”和其他 AI 的话，让它知道大家目前说到哪。
    return messages


def _last_user_message_index(conversation: Conversation) -> int:
    for index in range(len(conversation.messages) - 1, -1, -1):
        if conversation.messages[index].role == "user":
            return index
    return -1


def _has_spoken(conversation: Conversation, speaker: str) -> bool:
    return bool(speaker) and any(message.speaker == speaker for message in conversation.messages)


def _has_ai_messages(conversation: Conversation) -> bool:
    return any(message.role == "ai" and not _is_summary(message) for message in conversation.messages)


def _format_messages(messages: list[Message]) -> str:
    parts: list[str] = []
    for message in messages:
        if message.role == "user":
            parts.append(f"{_speaker_label(message)}：\n{message.content}")
        else:
            parts.append(f"{_speaker_label(message)}：\n{message.content}\n{SEPARATOR}")
    return "\n\n".join(parts)


def _speaker_label(message: Message) -> str:
    if message.role == "user":
        return "我"
    return message.speaker


def _only_user_message(messages: list[Message]) -> bool:
    return len(messages) == 1 and messages[0].role == "user"


def _is_summary(message: Message) -> bool:
    return message.role == "summary" or message.speaker == "总结"
