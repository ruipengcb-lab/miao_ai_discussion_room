from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import urlparse

from nicegui import ui

import api_providers
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


SPEAKER_COLORS = {
    "我": ("#f0f7ff", "#24508d"),
    "喵酱": ("#f0f7ff", "#24508d"),
    "ChatGPT": ("#eefaf3", "#1d7a46"),
    "DeepSeek": ("#f1f3ff", "#4856b8"),
    "GLM": ("#fff4e6", "#c56b1d"),
    "MiniMax": ("#fff0f6", "#bc3b72"),
    "总结": ("#f5f1ff", "#6a47ad"),
}
FALLBACK_COLORS = [
    ("#eefaf3", "#1d7a46"),
    ("#f1f3ff", "#4856b8"),
    ("#fff4e6", "#c56b1d"),
    ("#fff0f6", "#bc3b72"),
    ("#eff8f8", "#1f7a7a"),
    ("#f5f1ff", "#6a47ad"),
    ("#edf7ed", "#477a2f"),
    ("#fff1ed", "#b9533a"),
    ("#eef6ff", "#2e6da3"),
    ("#f7f1e8", "#8a5a22"),
    ("#f1f7f5", "#2f7666"),
    ("#f8f0fa", "#9a4ba3"),
]
SUMMARY_AI_URL = "https://chat.deepseek.com/"


class DiscussionUI:
    """NiceGUI 界面层：负责交互和展示，不直接处理存储细节。"""

    def __init__(self, conversation: Conversation) -> None:
        self.conversation = conversation
        self._is_maximized = False
        self._maximize_btn = None
        self.prompt_ai_name = conversation.participants[0]
        self.import_ai_name = conversation.participants[0]
        self.history_container = None
        self.prompt_preview = None
        self.topic_input = None
        self.topic_display = None
        self.topic_edit_container = None
        self.participants_container = None
        self.new_ai_input = None
        self.user_input = None
        self.ai_reply_input = None
        self.prompt_select = None
        self.prompt_profile_select = None
        self.import_select = None
        self.add_ai_button = None
        self.count_label = None
        self.archives_container = None
        self.rounds_container = None
        self.round_tabs_container = None
        self.active_round_index = 999999
        self.prompt_mode = "discussion"
        # API 设置（按 AI 名字存储）
        settings = load_settings()
        self.auto_mode = bool(settings.get("auto_mode", False))
        self.per_ai_api: dict[str, dict] = dict(settings.get("per_ai_api", {}))
        self.ai_modes: dict[str, str] = dict(settings.get("ai_modes", {}))
        self.prompt_profiles, self.active_prompt_profile_id = normalize_prompt_profiles(settings)
        self._status_label = None  # 动态渲染的状态区

    def build(self) -> None:
        ui.page_title("喵酱 AI 讨论室")
        self._styles()

        with ui.column().classes("app-shell"):
            self._build_header()
            with ui.row().classes("main-grid"):
                self._build_left_panel()
                self._build_center_panel()
                self._build_right_panel()

        self.refresh_all()

    def _build_header(self) -> None:
        with ui.row().classes("topbar"):
            with ui.column().classes("title-block"):
                ui.label("喵酱 AI 讨论室").classes("app-title")
            with ui.row().classes("top-actions"):
                ui.button("保存 TXT", icon="save", on_click=self.save_as_txt).props("flat").classes("ghost-btn")
                ui.button("下载 JSON", icon="data_object", on_click=self.download_json).props("flat").classes("ghost-btn")
                ui.button("下载 Markdown", icon="download", on_click=self.download_markdown).props("flat").classes("ghost-btn")
                self._maximize_btn = ui.button(icon="crop_square", on_click=self._toggle_maximize).props("flat round dense").classes("window-ctrl-btn").tooltip("最大化")
                ui.button(icon="remove", on_click=self._minimize_window).props("flat round dense").classes("window-ctrl-btn").tooltip("最小化")
                ui.button(icon="close", on_click=self.stop_server).props("flat round dense").classes("window-close-btn").tooltip("关闭")

    def _build_left_panel(self) -> None:
        with ui.column().classes("panel side-panel"):
            ui.label("讨论设置").classes("panel-title")
            with ui.row().classes("topic-row"):
                self.topic_display = ui.label(self._topic_display_text()).classes("topic-display")
                ui.button(icon="edit", on_click=self.show_topic_editor).props("flat round dense").classes("mini-icon-btn")
            self.topic_edit_container = ui.column().classes("topic-edit hidden")
            with self.topic_edit_container:
                self.topic_input = ui.input("讨论主题", value=self.conversation.title, placeholder="输入这次要讨论的话题").props("outlined dense").classes("full")
                with ui.row().classes("dialog-actions"):
                    ui.button("取消", on_click=self.hide_topic_editor).props("flat dense").classes("ghost-btn compact-btn")
                    ui.button("保存", on_click=self.save_topic_editor).props("dense").classes("primary-btn compact-btn")
            ui.button("创建新话题", icon="add_circle", on_click=self.new_topic).classes("ghost-btn full")

            with ui.row().classes("section-title-row"):
                ui.label("AI 发言者").classes("subtle-label")
                ui.button(icon="add", on_click=lambda: self.edit_ai_url("")).props("flat round dense").classes("mini-icon-btn").tooltip("添加 AI 发言者")
            self.participants_container = ui.column().classes("participant-list")

            ui.separator().classes("soft-separator")
            ui.label("我发言").classes("panel-title small-title")
            self.user_input = ui.textarea("输入你的观点、问题或追问").classes("full draft-box")
            ui.button("加入我的发言", icon="add_comment", on_click=self.add_user_message).classes("primary-btn full")

            ui.separator().classes("soft-separator")
            with ui.row().classes("panel-head"):
                ui.label("历史话题").classes("panel-title small-title")
                ui.button(icon="refresh", on_click=self.refresh_archives).props("flat round dense").classes("mini-icon-btn")
            self.archives_container = ui.column().classes("archive-list")

    def _build_center_panel(self) -> None:
        with ui.column().classes("panel history-panel"):
            with ui.row().classes("panel-head"):
                ui.label("对话记录").classes("panel-title")
                self.count_label = ui.label("").classes("count-pill")
            self.round_tabs_container = ui.row().classes("round-tabs")
            self.history_container = ui.column().classes("history-scroll")
            with self.history_container:
                self.rounds_container = ui.column().classes("round-list")

    def _build_right_panel(self) -> None:
        with ui.column().classes("panel side-panel"):
            with ui.row().classes("panel-head"):
                ui.label("生成给 AI 的 Prompt").classes("panel-title")
                ui.button(icon="add", on_click=self.show_prompt_template_dialog).props("flat round dense").classes("mini-icon-btn").tooltip("管理 Prompt 模板")
            self.prompt_profile_select = ui.select(
                self._prompt_profile_options(),
                value=self.active_prompt_profile_id,
                label="Prompt 模板",
                on_change=self.on_prompt_profile_change,
            ).classes("full")
            self.prompt_select = ui.select(
                [*self.conversation.participants, "总结"],
                value=self.prompt_ai_name,
                label="要粘贴到哪个 AI 网页",
                on_change=self.on_prompt_ai_change,
            ).classes("full")
            self.prompt_preview = ui.textarea("Prompt 预览（可手动修改）").classes("full prompt-box")
            with ui.row().classes("button-row"):
                ui.button("重新生成 Prompt", on_click=self.refresh_prompt).classes("ghost-btn")
                ui.button("复制当前 Prompt", on_click=self.copy_prompt).classes("primary-btn")
            ui.button("生成总结 Prompt", icon="summarize", on_click=self.refresh_summary_prompt).classes("ghost-btn full")

            ui.separator().classes("soft-separator")
            ui.label("把 AI 网页回复加入讨论").classes("panel-title small-title")
            self.import_select = ui.select(
                [*self.conversation.participants, "总结"],
                value=self.import_ai_name,
                label="这段回复来自谁",
                on_change=self.on_import_ai_change,
            ).classes("full")
            self.ai_reply_input = ui.textarea("粘贴 AI / 总结返回内容").classes("full reply-box")
            with ui.row().classes("button-row"):
                self.add_ai_button = ui.button(self._add_ai_button_label(), on_click=self.add_ai_message).classes("primary-btn full")
                ui.button("打开 AI 网页", icon="open_in_new", on_click=self._open_import_ai_url).classes("ghost-btn full")

    def _participant_add_ai(self, name: str) -> None:
        """左侧 participant card 的「加入讨论」按钮：先切 import_ai_name 再调 add_ai_message。"""
        self.import_ai_name = name
        self.import_select.value = name
        self.add_ai_message()

    def _open_import_ai_url(self) -> None:
        """右下角「打开 AI 网页」按钮。"""
        self.open_ai_url(self.import_ai_name)

    def _enable_auto_mode(self) -> None:
        """从右侧面板开启自动模式（需要先配置 API）。"""
        self.auto_mode = True
        save_settings(self._current_settings())
        self.refresh_all()
        ui.notify("自动模式已开启。请先在 AI 发言者的「网页地址」弹窗里配置 API Key。", type="info")

    def _current_settings(self) -> dict:
        return {
            "auto_mode": self.auto_mode,
            "per_ai_api": self.per_ai_api,
            "ai_modes": self.ai_modes,
            "prompt_profiles": self.prompt_profiles,
            "active_prompt_profile_id": self.active_prompt_profile_id,
        }

    def apply_settings(self, sync_selects: bool = True) -> None:
        self.conversation.set_title(str(self.topic_input.value or self.conversation.title or ""))
        self.refresh_topic_display()
        if sync_selects:
            self._sync_select_options()
        self.save(silent=True)

    # ------------------------------------------------------------------ Topic
    def show_topic_editor(self) -> None:
        self.topic_input.value = self.conversation.title
        self.topic_edit_container.classes(remove="hidden")

    def hide_topic_editor(self) -> None:
        self.topic_input.value = self.conversation.title
        self.topic_edit_container.classes(add="hidden")

    def save_topic_editor(self) -> None:
        self.conversation.set_title(str(self.topic_input.value or ""))
        self.refresh_topic_display()
        self.topic_edit_container.classes(add="hidden")
        self.save(silent=True)

    def refresh_topic_display(self) -> None:
        if self.topic_display:
            self.topic_display.text = self._topic_display_text()

    # ------------------------------------------------------------------ User message
    def add_user_message(self) -> None:
        content = str(self.user_input.value or "").strip()
        if not content:
            ui.notify("先输入一段我的发言。", type="warning")
            return
        self.apply_settings()
        self.conversation.add_user_message(content)
        self.user_input.value = ""
        self.active_round_index = 999999
        self.save(silent=True)
        self.refresh_all()

    # ------------------------------------------------------------------ AI message
    def add_ai_message(self) -> None:
        if self._selected_import_auto_enabled():
            ui.notify("正在自动调用 API...", type="info")
            ui.update()
            ui.timer(0.05, lambda: self._auto_add_ai_message(), once=True)
            return

        content = str(self.ai_reply_input.value or "").strip()
        if not content:
            ui.notify("先粘贴 AI 的回复内容，再加入对话记录。", type="warning")
            return
        self._do_add_ai_message(content)

    def _do_add_ai_message(self, content: str) -> None:
        self.apply_settings()
        if self.import_ai_name == "总结":
            self.conversation.add_message("总结", "summary", content)
        else:
            self.conversation.add_ai_message(self.import_ai_name, content)
        self.ai_reply_input.value = ""
        if self.import_ai_name != "总结":
            self._advance_prompt_target_after(self.import_ai_name)
        self.active_round_index = 999999
        self.save(silent=True)
        self.refresh_all()

    async def _auto_add_ai_message(self) -> None:
        """自动模式：生成 prompt → 调用对应 AI 的 API → 加入讨论。"""
        ai_name = self.import_ai_name
        api_info = self.per_ai_api.get(ai_name, {})
        api_key = api_info.get("api_key", "")

        if not api_key:
            ui.notify(f"「{ai_name}」尚未配置 API Key。请先在「{ai_name}」的网页地址弹窗里填写。", type="warning")
            return

        prompt = str(self.prompt_preview.value or "").strip()
        if not prompt:
            ui.notify("Prompt 为空，先生成一个。", type="warning")
            self.refresh_prompt()
            return

        ui.notify(f"正在调用 {ai_name} API，请稍候...", type="info")
        ui.update()

        try:
            provider_key = api_info.get("provider", "deepseek")
            model = api_info.get("model") or None
            config = api_providers.build_api_config(provider_key, api_key, model)
            provider = api_providers.create_provider(config)
            if provider is None:
                ui.notify(f"不支持的 Provider：{provider_key}", type="negative")
                return
            content = await provider.call(prompt)
        except Exception as e:
            ui.notify(f"API 调用出错：{e}", type="negative")
            return

        if content is None:
            ui.notify(f"{ai_name} API 返回为空，请检查 API Key 和余额。", type="negative")
            return

        self.ai_reply_input.value = content
        self._do_add_ai_message(content)

    def clear_conversation(self) -> None:
        self.conversation.clear()
        self.save(silent=True)
        self.refresh_all()
        ui.notify("当前讨论已清空。", type="info")

    def new_topic(self) -> None:
        with ui.dialog() as dialog, ui.card().classes("url-dialog"):
            ui.label("创建新话题").classes("panel-title")
            topic_input = ui.input("新话题", placeholder="输入这次要讨论的话题").classes("full")
            with ui.row().classes("dialog-actions"):
                ui.button("取消", on_click=dialog.close).props("flat").classes("ghost-btn")
                ui.button("创建", on_click=lambda: self.create_new_topic(topic_input.value, dialog)).classes("primary-btn")
        dialog.open()

    def create_new_topic(self, title: str, dialog) -> None:
        self.apply_settings()
        archived = None
        if self.conversation.title or self.conversation.messages:
            archived = archive_conversation(self.conversation)
        participants = self.conversation.participants.copy()
        participant_urls = self.conversation.participant_urls.copy()
        self.conversation = Conversation(title=title.strip(), participants=participants)
        self.conversation.participant_urls.update({name: participant_urls.get(name, "") for name in participants})
        self.topic_input.value = self.conversation.title
        self.refresh_topic_display()
        self.topic_edit_container.classes(add="hidden")
        self.user_input.value = ""
        self.ai_reply_input.value = ""
        self.active_round_index = 999999
        self.prompt_ai_name = participants[0]
        self.import_ai_name = participants[0]
        self.prompt_mode = "discussion"
        self._sync_select_options()
        self.save(silent=True)
        self.refresh_all()
        dialog.close()
        if archived:
            ui.notify(f"已创建新话题，旧话题已保存：{archived.name}", type="positive")
        else:
            ui.notify("已创建新话题。", type="positive")

    def open_archived_topic(self, path_text: str) -> None:
        self.apply_settings()
        archive_conversation(self.conversation)
        self.conversation = load_archived_conversation(path_text)
        self.topic_input.value = self.conversation.title
        self.refresh_topic_display()
        self.active_round_index = 999999
        self.prompt_ai_name = self.conversation.participants[0]
        self.import_ai_name = self.conversation.participants[0]
        self._sync_select_options()
        self.save(silent=True)
        ui.notify("已打开历史话题。", type="positive")
        self.refresh_all()

    def delete_archived_topic(self, path_text: str) -> None:
        delete_archived_conversation(path_text)
        ui.notify("历史话题已删除。", type="info")
        self.refresh_archives()

    def delete_message_by_content(self, message) -> None:
        index = self.conversation.message_index(message)
        if index >= 0:
            self.conversation.delete_message(index)
            self.save(silent=True)
            self.refresh_all()

    # ------------------------------------------------------------------ AI URL + API 设置弹窗
    def edit_ai_url(self, name: str) -> None:
        is_new = not bool(name)
        is_summary = name == "总结"
        current_name = name or self._next_ai_name()
        with ui.dialog() as dialog, ui.card().classes("url-dialog"):
            ui.label("添加 AI 发言者" if is_new else f"「{name}」网页地址 & API").classes("panel-title")

            name_input = ui.input(
                "AI 名称",
                value=current_name,
                placeholder="例如 Kimi、Claude、Perplexity",
            ).props("outlined dense").classes("full")
            if is_summary:
                name_input.set_enabled(False)

            # 已有 API 配置
            existing = self.per_ai_api.get(current_name, {})
            current_provider = existing.get("provider", "deepseek")
            current_key = existing.get("api_key", "")

            default_url = DEFAULT_PARTICIPANT_URLS.get(current_name, "")
            url_input = ui.input(
                "🌐 网页地址（可选）",
                value=self.conversation.participant_urls.get(current_name, default_url),
                placeholder=default_url or "https://...",
            ).props("outlined dense").classes("full")

            # API 配置区
            ui.label("API 配置（可选）").classes("muted-text").style("font-size:12px;font-weight:600;margin-top:4px;")
            ui.label("不同服务商的 API Key 不通用；这里决定自动调用哪家的接口。").classes("muted-text")

            # Provider 选择
            provider_options = api_providers.all_providers()
            provider_select = ui.select(
                provider_options,
                value=current_provider,
                label="服务商",
            ).props("outlined dense").classes("full")

            # API Key（密码类型）
            key_input = ui.input(
                "🔑 API Key",
                value=current_key,
                placeholder="sk-...",
                password=True,
                password_toggle_button=True,
            ).props("outlined dense").classes("full")
            status_row = ui.row().classes("api-status-row")
            with status_row:
                if current_key:
                    ui.label(f"{api_providers.provider_display_name(current_provider)} API 已配置，可自动加入").classes("configured-label")
                else:
                    ui.label("未填写 API Key，将使用手动粘贴模式").classes("muted-text")

            def _on_provider_change(e):
                pname = api_providers.provider_display_name(e.value)
                status_row.clear()
                with status_row:
                    if key_input.value:
                        ui.label(f"{pname} API 已配置，可自动加入").classes("configured-label")
                    else:
                        ui.label("未填写 API Key，将使用手动粘贴模式").classes("muted-text")

            provider_select.on_value_change(_on_provider_change)

            with ui.row().classes("dialog-actions"):
                ui.button("取消", on_click=dialog.close).props("flat").classes("dialog-btn")
                ui.button(
                    "保存",
                    on_click=lambda: self._save_ai_url_and_api(
                        original_name=name,
                        name=name_input.value,
                        url=url_input.value,
                        provider=provider_select.value,
                        api_key=key_input.value,
                        model="",
                        dialog=dialog,
                    ),
                ).classes("primary-btn dialog-btn")

        dialog.open()

    def _save_ai_url_and_api(self, original_name: str, name: str, url: str, provider: str, api_key: str, model: str, dialog) -> None:
        name = str(name or "").strip()
        original_name = str(original_name or "").strip()
        if not name:
            ui.notify("先填写 AI 名称。", type="warning")
            return
        is_summary = original_name == "总结" or name == "总结"
        if name != original_name and name in self.conversation.participants:
            ui.notify("这个 AI 名称已经存在。", type="warning")
            return

        if is_summary:
            name = "总结"
        elif original_name and original_name in self.conversation.participants and name != original_name:
            old_url = self.conversation.participant_urls.get(original_name, "")
            old_api = self.per_ai_api.get(original_name)
            self.conversation.set_participants([
                name if item == original_name else item for item in self.conversation.participants
            ])
            self.conversation.participant_urls.pop(original_name, None)
            self.per_ai_api.pop(original_name, None)
            old_mode = self.ai_modes.pop(original_name, "auto")
            self.conversation.participant_urls[name] = url or old_url
            if old_api:
                self.per_ai_api[name] = old_api
            self.ai_modes[name] = old_mode
        elif name not in self.conversation.participants:
            self.conversation.set_participants([*self.conversation.participants, name])

        # 保存 URL
        if is_summary:
            self.conversation.participant_urls[name] = url.strip()
        else:
            self.conversation.set_participant_url(name, url)

        # 保存 API 配置
        if api_key.strip():
            self.per_ai_api[name] = {
                "provider": provider,
                "api_key": api_key.strip(),
                "model": model.strip() or "",  # 空字符串用默认
            }
        else:
            # 删掉这个 AI 的 API 配置（留空 = 手动模式）
            self.per_ai_api.pop(name, None)
            self.ai_modes[name] = "manual"

        save_settings(self._current_settings())
        self.save(silent=True)
        self._sync_select_options()
        ui.notify(f"「{name}」已保存。", type="positive")
        dialog.close()
        self.refresh_participants()
        self._refresh_auto_button()

    # ------------------------------------------------------------------ 通用
    def save(self, silent: bool = False) -> None:
        save_conversation(self.conversation)
        if not silent:
            ui.notify("已保存到 data/current_conversation.json", type="positive")

    def save_as_txt(self) -> None:
        self.apply_settings()
        filename = self._download_filename("txt")
        self._save_file_with_picker(self._txt_text(), filename, "text/plain")

    def download_json(self) -> None:
        self.apply_settings()
        filename = self._download_filename("json")
        content = json.dumps(self.conversation.to_dict(), ensure_ascii=False, indent=2)
        self._save_file_with_picker(content, filename, "application/json")

    def download_markdown(self) -> None:
        self.apply_settings()
        filename = self._download_filename("md")
        self._save_file_with_picker(self._markdown_text(), filename, "text/markdown")

    def stop_server(self) -> None:
        """关闭窗口（frameless 模式下的关闭按钮）"""
        with ui.dialog() as dialog, ui.card().classes("url-dialog"):
            ui.label("确认关闭喵酱讨论室？").classes("panel-title")
            with ui.row().classes("dialog-actions"):
                ui.button("取消", on_click=dialog.close).props("flat").classes("ghost-btn")
                ui.button("确认关闭", icon="close", on_click=lambda: self._do_stop(dialog)).classes("danger-btn")
        dialog.open()

    def _toggle_maximize(self) -> None:
        """切换最大化/还原"""
        from nicegui import app
        w = app.native.main_window
        if w is None:
            return
        if self._is_maximized:
            w.restore()
            self._is_maximized = False
            if self._maximize_btn:
                self._maximize_btn.props('icon=crop_square')
                self._maximize_btn.tooltip('最大化')
        else:
            w.maximize()
            self._is_maximized = True
            if self._maximize_btn:
                self._maximize_btn.props('icon=filter_none')
                self._maximize_btn.tooltip('还原')

    def _minimize_window(self) -> None:
        """最小化原生窗口"""
        from nicegui import app
        w = app.native.main_window
        if w:
            w.minimize()

    def _do_stop(self, dialog) -> None:
        import os
        ui.notify("正在关闭...", type="info")
        from nicegui import app
        w = app.native.main_window
        if w:
            w.destroy()

        def _shutdown():
            os._exit(0)

        ui.timer(0.5, _shutdown, once=True)

    def copy_prompt(self) -> None:
        current_prompt = str(self.prompt_preview.value or "")
        ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(current_prompt, ensure_ascii=False)})")
        opened = self.open_ai_url("总结" if self.prompt_mode == "summary" else self.prompt_ai_name, silent=True)
        ui.notify("当前 Prompt 已复制，已打开对应网页。" if opened else "当前 Prompt 已复制。", type="positive")

    # ------------------------------------------------------------------ Refresh
    def refresh_all(self) -> None:
        self.refresh_participants()
        self.refresh_archives()
        self.refresh_history()
        self.refresh_prompt()
        self._refresh_auto_button()

    def _refresh_auto_button(self) -> None:
        if self.add_ai_button:
            self.add_ai_button.set_text(self._add_ai_button_label())

    def _selected_import_auto_enabled(self) -> bool:
        api_info = self.per_ai_api.get(self.import_ai_name, {})
        return bool(api_info.get("api_key", "")) and self.ai_modes.get(self.import_ai_name, "auto") == "auto"

    def _add_ai_button_label(self) -> str:
        return "自动加入" if self._selected_import_auto_enabled() else "加入对话记录"

    def refresh_participants(self) -> None:
        self.participants_container.clear()
        with self.participants_container:
            for name in [*self.conversation.participants, "总结"]:
                background, accent = self._speaker_color(name)
                api_info = self.per_ai_api.get(name, {})
                has_api = bool(api_info.get("api_key", ""))
                is_auto = self.ai_modes.get(name, "auto") == "auto"
                has_url = bool(self._normalized_url(self.conversation.participant_urls.get(name, "")))
                with ui.column().classes("participant-item").style(
                    f"background: {background}; border-left: 5px solid {accent};"
                ):
                    with ui.row().classes("participant-head"):
                        with ui.row().classes("speaker-row"):
                            ui.element("span").classes("speaker-dot").style(f"background: {accent};")
                            ui.label(name).classes("participant-name").style(f"color: {accent};")
                            if has_url:
                                ui.label("🔗").classes("status-icon").tooltip("已填写网页地址")
                            if has_api:
                                ui.label("🔑").classes("status-icon").tooltip("已填写 API Key")
                        if name != "总结":
                            removable = len(self.conversation.participants) > 1
                            ui.button(icon="close", on_click=lambda n=name: self.remove_participant(n)).props(
                                "flat round dense"
                            ).classes("remove-ai-btn").set_enabled(removable)
                    with ui.row().classes("participant-actions"):
                        mode_label = "自动" if has_api and is_auto else "手动"
                        mode_class = "mode-btn auto-mode-btn" if has_api and is_auto else "mode-btn manual-mode-btn"
                        ui.button(mode_label, on_click=lambda n=name: self.toggle_ai_mode(n)).props(
                            "flat dense"
                        ).classes(f"compact-btn {mode_class}").set_enabled(has_api)
                        ui.button("网页 / API", icon="tune", on_click=lambda n=name: self.edit_ai_url(n)).props(
                            "flat dense"
                        ).classes("compact-btn api-setup-btn")

    def toggle_ai_mode(self, name: str) -> None:
        if not self.per_ai_api.get(name, {}).get("api_key", ""):
            ui.notify("这个 AI 没有 API Key，只能使用手动模式。", type="info")
            return
        self.ai_modes[name] = "manual" if self.ai_modes.get(name, "auto") == "auto" else "auto"
        save_settings(self._current_settings())
        self.refresh_participants()
        self._refresh_auto_button()

    def refresh_archives(self) -> None:
        self.archives_container.clear()
        archives = list_archived_conversations()
        with self.archives_container:
            if not archives:
                ui.label("还没有历史话题").classes("muted-text")
                return
            for item in archives[:12]:
                with ui.column().classes("archive-item"):
                    ui.label(str(item["title"] or "无标题")).classes("archive-title")
                    ui.label(f"{item['message_count']} 条 / {item['updated_at']}").classes("archive-meta")
                    with ui.row().classes("archive-actions"):
                        ui.button("打开", icon="open_in_new", on_click=lambda p=item["path"]: self.open_archived_topic(str(p))).props(
                            "flat dense"
                        ).classes("archive-open-btn")
                        ui.button("删除", icon="delete", on_click=lambda p=item["path"]: self.delete_archived_topic(str(p))).props(
                            "flat dense"
                        ).classes("archive-delete-btn")

    def refresh_history(self) -> None:
        rounds = self._group_rounds()
        if rounds and (self.active_round_index < 0 or self.active_round_index >= len(rounds)):
            self.active_round_index = len(rounds) - 1

        self.refresh_round_tabs(rounds)
        self.rounds_container.clear()
        self.count_label.text = f"{len(self.conversation.messages)} 条"
        with self.rounds_container:
            if not self.conversation.messages:
                with ui.column().classes("empty-state"):
                    ui.icon("auto_awesome").classes("empty-icon")
                    ui.label("还没有发言").classes("empty-title")
                    ui.label("先输入主题和我的发言，再复制 Prompt 去邀请第一个 AI。").classes("empty-copy")
                return

            round_messages = rounds[self.active_round_index]
            with ui.column().classes("round-block"):
                for idx, message in enumerate(round_messages):
                    self._render_message(message, idx)

    def refresh_round_tabs(self, rounds) -> None:
        self.round_tabs_container.clear()
        with self.round_tabs_container:
            if not rounds:
                return
            for index, _round_messages in enumerate(rounds):
                active_class = "round-tab active-round-tab" if index == self.active_round_index else "round-tab"
                label = self._round_tab_label(index, _round_messages)
                ui.button(
                    label,
                    on_click=lambda i=index: self.select_round(i),
                ).props("unelevated dense").classes(active_class)

    def select_round(self, index: int) -> None:
        self.active_round_index = index
        self.refresh_history()

    def _render_message(self, message, index_in_round: int) -> None:
        speaker_label = self._display_speaker(message)
        background, accent = self._speaker_color(speaker_label)
        with ui.column().classes("message-card").style(
            f"background: {background}; border-left: 5px solid {accent};"
        ):
            with ui.row().classes("message-meta"):
                with ui.row().classes("speaker-row"):
                    ui.element("span").classes("speaker-dot").style(f"background: {accent};")
                    ui.label(speaker_label).classes("speaker").style(f"color: {accent};")
                with ui.row().classes("message-meta-right"):
                    ui.label(message.created_at.replace("T", " ")).classes("time")
                    ui.button(
                        icon="delete",
                        on_click=lambda m=message: self.delete_message_by_content(m),
                    ).props("flat round dense").classes("delete-msg-btn")
            self._render_message_content(message.content)

    def _render_message_content(self, content: str) -> None:
        # 使用 ui.markdown() 渲染，保留 NiceGUI 的 markdown 安全处理
        if len(content) <= 520:
            ui.markdown(content).classes("message-content")
            return

        snippet = content[:520].rstrip() + "\n\n..."
        expanded = {"value": False}
        container = ui.column().classes("collapsible-message")

        def render() -> None:
            container.clear()
            with container:
                if expanded["value"]:
                    ui.markdown(content).classes("message-content")
                    ui.button("收起", icon="unfold_less", on_click=lambda: toggle(False)).props("flat dense").classes("fold-btn")
                else:
                    ui.markdown(snippet).classes("message-content collapsed-preview")
                    ui.button("展开全文", icon="unfold_more", on_click=lambda: toggle(True)).props("flat dense").classes("fold-btn")

        def toggle(value: bool) -> None:
            expanded["value"] = value
            render()

        render()

    def _group_rounds(self):
        rounds = []
        current = []
        for message in self.conversation.messages:
            if message.role == "user" and current:
                rounds.append(current)
                current = []
            current.append(message)
        if current:
            rounds.append(current)
        return rounds

    def _round_tab_label(self, index: int, round_messages) -> str:
        user_text = ""
        for message in round_messages:
            if message.role == "user":
                user_text = message.content.strip().replace("\n", " ")
                break
        if len(user_text) > 16:
            user_text = user_text[:16] + "..."
        # 用「轮次编号」代替 emoji 图标
        return f"{index + 1}"

    def refresh_prompt(self) -> None:
        self.prompt_mode = "discussion"
        self.prompt_ai_name = self.prompt_select.value or self.prompt_ai_name
        self.apply_settings(sync_selects=False)
        if self.prompt_ai_name == "总结":
            self.prompt_mode = "summary"
            self.prompt_preview.value = build_summary_prompt(self.conversation, self._active_prompt_profile())
        else:
            self.prompt_preview.value = build_prompt(self.conversation, self.prompt_ai_name, self._active_prompt_profile())

    def refresh_summary_prompt(self) -> None:
        self.prompt_mode = "summary"
        self.apply_settings(sync_selects=False)
        self.prompt_preview.value = build_summary_prompt(self.conversation, self._active_prompt_profile())

    def on_prompt_ai_change(self, event) -> None:
        self.prompt_ai_name = event.value
        self.refresh_prompt()

    def on_prompt_profile_change(self, event) -> None:
        self.active_prompt_profile_id = event.value or self.active_prompt_profile_id
        save_settings(self._current_settings())
        self.refresh_prompt()

    def _prompt_profile_options(self) -> dict[str, str]:
        return {profile["id"]: profile["name"] for profile in self.prompt_profiles}

    def _active_prompt_profile(self) -> dict:
        for profile in self.prompt_profiles:
            if profile["id"] == self.active_prompt_profile_id:
                return profile
        return self.prompt_profiles[0]

    def show_prompt_template_dialog(self) -> None:
        with ui.dialog() as dialog, ui.card().classes("prompt-template-dialog"):
            with ui.row().classes("panel-head"):
                ui.label("Prompt 模板").classes("panel-title")
                ui.button(icon="help_outline", on_click=self.show_prompt_help_dialog).props("flat round dense").classes("mini-icon-btn").tooltip("占位符说明")
            ui.label("模板框留空时，会使用内置接力逻辑。").classes("muted-text")

            profile_select = ui.select(
                self._prompt_profile_options(),
                value=self.active_prompt_profile_id,
                label="当前模板",
            ).props("outlined dense").classes("full")
            name_input = ui.input("模板名称", value=self._active_prompt_profile()["name"]).props("outlined dense").classes("full")
            matrix_state = {"matrix": [[""]], "round": 1, "turn": 1}
            with ui.row().classes("button-row"):
                round_select = ui.select({1: "第 1 轮"}, value=1, label="讨论轮次").props("outlined dense").classes("full")
                turn_select = ui.select({1: "第 1 个 AI"}, value=1, label="AI 顺序").props("outlined dense").classes("full")
            prompt_cell_input = ui.textarea("当前格子的 Prompt").props("outlined").classes("full template-box")
            summary_input = ui.textarea("总结 Prompt").props("outlined").classes("full template-box")

            def _matrix_options(count: int, label: str) -> dict[int, str]:
                return {index: f"第 {index} {label}" for index in range(1, count + 1)}

            def normalize_matrix(matrix) -> list[list[str]]:
                rows = []
                for row in matrix or [[""]]:
                    rows.append([str(cell) for cell in row] if isinstance(row, list) else [str(row)])
                max_cols = max((len(row) for row in rows), default=1)
                return [row + [""] * (max_cols - len(row)) for row in rows] or [[""]]

            def save_current_cell() -> None:
                row = matrix_state["round"] - 1
                col = matrix_state["turn"] - 1
                matrix_state["matrix"][row][col] = str(prompt_cell_input.value or "")

            def refresh_matrix_selects() -> None:
                matrix = matrix_state["matrix"]
                round_select.set_options(_matrix_options(len(matrix), "轮"), value=matrix_state["round"])
                turn_select.set_options(_matrix_options(len(matrix[0]), "个 AI"), value=matrix_state["turn"])
                prompt_cell_input.value = matrix[matrix_state["round"] - 1][matrix_state["turn"] - 1]

            def load_profile(profile_id: str) -> None:
                profile = next((item for item in self.prompt_profiles if item["id"] == profile_id), self._active_prompt_profile())
                name_input.value = profile["name"]
                matrix = profile.get("prompt_matrix")
                if not matrix:
                    prompts = list(profile.get("round_prompts") or [])
                    matrix = [[value] for value in prompts] if prompts else [[""]]
                matrix_state["matrix"] = normalize_matrix(matrix)
                matrix_state["round"] = 1
                matrix_state["turn"] = 1
                refresh_matrix_selects()
                summary_input.value = profile["summary"]

            def collect_profile(profile_id: str | None = None) -> dict:
                save_current_cell()
                matrix = [[cell.strip() for cell in row] for row in matrix_state["matrix"]]
                return {
                    "id": profile_id or self._new_prompt_profile_id(str(name_input.value or "新模板")),
                    "name": str(name_input.value or "新模板").strip() or "新模板",
                    "first_round": matrix[0][0] if matrix and matrix[0] else "",
                    "later_round": "",
                    "round_prompts": [row[0] if row else "" for row in matrix],
                    "prompt_matrix": matrix,
                    "summary": str(summary_input.value or "").strip(),
                }

            def on_round_change(e) -> None:
                save_current_cell()
                matrix_state["round"] = int(e.value or 1)
                prompt_cell_input.value = matrix_state["matrix"][matrix_state["round"] - 1][matrix_state["turn"] - 1]

            def on_turn_change(e) -> None:
                save_current_cell()
                matrix_state["turn"] = int(e.value or 1)
                prompt_cell_input.value = matrix_state["matrix"][matrix_state["round"] - 1][matrix_state["turn"] - 1]

            def add_round_prompt() -> None:
                save_current_cell()
                matrix_state["matrix"].append([""] * len(matrix_state["matrix"][0]))
                matrix_state["round"] = len(matrix_state["matrix"])
                refresh_matrix_selects()

            def add_turn_prompt() -> None:
                save_current_cell()
                for row in matrix_state["matrix"]:
                    row.append("")
                matrix_state["turn"] = len(matrix_state["matrix"][0])
                refresh_matrix_selects()

            def remove_round_prompt() -> None:
                if len(matrix_state["matrix"]) <= 1:
                    ui.notify("至少保留一轮。", type="warning")
                    return
                save_current_cell()
                matrix_state["matrix"].pop()
                matrix_state["round"] = min(matrix_state["round"], len(matrix_state["matrix"]))
                refresh_matrix_selects()

            def remove_turn_prompt() -> None:
                if len(matrix_state["matrix"][0]) <= 1:
                    ui.notify("至少保留一个 AI 位置。", type="warning")
                    return
                save_current_cell()
                for row in matrix_state["matrix"]:
                    row.pop()
                matrix_state["turn"] = min(matrix_state["turn"], len(matrix_state["matrix"][0]))
                refresh_matrix_selects()

            def save_current() -> None:
                profile_id = str(profile_select.value or self.active_prompt_profile_id)
                new_profile = collect_profile(profile_id)
                self.prompt_profiles = [
                    new_profile if profile["id"] == profile_id else profile
                    for profile in self.prompt_profiles
                ]
                self.active_prompt_profile_id = profile_id
                self._sync_prompt_profile_select()
                save_settings(self._current_settings())
                self.refresh_prompt()
                ui.notify("Prompt 模板已保存。", type="positive")

            def save_as_new() -> None:
                new_profile = collect_profile()
                self.prompt_profiles.append(new_profile)
                self.active_prompt_profile_id = new_profile["id"]
                profile_select.set_options(self._prompt_profile_options(), value=new_profile["id"])
                self._sync_prompt_profile_select()
                save_settings(self._current_settings())
                self.refresh_prompt()
                ui.notify("已另存为新 Prompt 模板。", type="positive")

            def delete_current() -> None:
                profile_id = str(profile_select.value or "")
                if profile_id == "default":
                    ui.notify("默认模板不能删除，可以直接修改或另存为新模板。", type="warning")
                    return
                self.prompt_profiles = [profile for profile in self.prompt_profiles if profile["id"] != profile_id]
                self.active_prompt_profile_id = self.prompt_profiles[0]["id"]
                profile_select.set_options(self._prompt_profile_options(), value=self.active_prompt_profile_id)
                self._sync_prompt_profile_select()
                load_profile(self.active_prompt_profile_id)
                save_settings(self._current_settings())
                self.refresh_prompt()
                ui.notify("Prompt 模板已删除。", type="info")

            profile_select.on_value_change(lambda e: load_profile(str(e.value)))
            round_select.on_value_change(on_round_change)
            turn_select.on_value_change(on_turn_change)
            load_profile(self.active_prompt_profile_id)

            with ui.row().classes("template-control-row"):
                with ui.row().classes("template-button-group"):
                    ui.button("增加轮次", icon="add", on_click=add_round_prompt).props("flat").classes("ghost-btn dialog-btn")
                    ui.button("删除最后一轮", icon="remove", on_click=remove_round_prompt).props("flat").classes("ghost-btn dialog-btn")
                with ui.row().classes("template-button-group"):
                    ui.button("增加 AI 位置", icon="add", on_click=add_turn_prompt).props("flat").classes("ghost-btn dialog-btn")
                    ui.button("删除最后 AI 位", icon="remove", on_click=remove_turn_prompt).props("flat").classes("ghost-btn dialog-btn")

            with ui.row().classes("dialog-actions"):
                ui.button("删除当前", on_click=delete_current).props("flat").classes("danger-ghost-btn dialog-btn")
                ui.button("另存为新模板", on_click=save_as_new).props("flat").classes("ghost-btn dialog-btn")
                ui.button("保存当前模板", on_click=save_current).classes("primary-btn dialog-btn")
                ui.button("关闭", on_click=dialog.close).props("flat").classes("ghost-btn dialog-btn")
        dialog.open()

    def _sync_prompt_profile_select(self) -> None:
        if self.prompt_profile_select:
            self.prompt_profile_select.set_options(self._prompt_profile_options(), value=self.active_prompt_profile_id)

    def show_prompt_help_dialog(self) -> None:
        with ui.dialog() as dialog, ui.card().classes("url-dialog"):
            ui.label("Prompt 占位符说明").classes("panel-title")
            ui.markdown(
                """
`{topic}`：当前讨论主题。

`{target_ai}`：这次要发给哪个 AI。

`{messages}`：自动整理好的接力上下文。第二个 AI 会看到“我 + 第一个 AI”，之后会看到本轮前面所有新发言；如果某个 AI 已经说过，再轮到它，会看到它上次发言之后的新内容。

`{latest_user_message}`：最近一次“我”的发言。

`{round}`：当前是第几轮用户问题。

`{turn}`：当前是这一轮里的第几个 AI 接力发言。

`{separator}`：AI 发言分隔符，通常不用手动写，因为 `{messages}` 里已经会自动加入。
                """
            ).classes("message-content")
            with ui.row().classes("dialog-actions"):
                ui.button("关闭", on_click=dialog.close).props("flat").classes("ghost-btn dialog-btn")
        dialog.open()

    def _new_prompt_profile_id(self, name: str) -> str:
        base = "".join(char.lower() if char.isalnum() else "_" for char in name).strip("_") or "prompt"
        profile_id = base
        existing = {profile["id"] for profile in self.prompt_profiles}
        index = 2
        while profile_id in existing:
            profile_id = f"{base}_{index}"
            index += 1
        return profile_id

    def _next_ai_name(self) -> str:
        base = "新 AI"
        existing = set(self.conversation.participants)
        if base not in existing:
            return base
        index = 2
        while f"{base} {index}" in existing:
            index += 1
        return f"{base} {index}"

    def on_import_ai_change(self, event) -> None:
        self.import_ai_name = event.value
        self._refresh_auto_button()

    def _sync_select_options(self) -> None:
        names = self.conversation.participants
        prompt_options = [*names, "总结"]
        if self.prompt_ai_name not in prompt_options:
            self.prompt_ai_name = names[0]
        self.prompt_select.set_options(prompt_options, value=self.prompt_ai_name)
        import_options = [*names, "总结"]
        if self.import_ai_name not in import_options:
            self.import_ai_name = names[0]
        self.import_select.set_options(import_options, value=self.import_ai_name)

    def add_participant(self, name: str | None = None) -> bool:
        name = str(name or "").strip()
        if not name:
            ui.notify("先输入 AI 名称。", type="warning")
            return False
        if name in self.conversation.participants:
            ui.notify("这个 AI 已经在列表里。", type="warning")
            return False
        self.conversation.set_participants([*self.conversation.participants, name])
        self._sync_select_options()
        self.save(silent=True)
        self.refresh_participants()
        self.refresh_prompt()
        return True

    def remove_participant(self, name: str) -> None:
        if len(self.conversation.participants) <= 1:
            ui.notify("至少保留一个 AI。", type="warning")
            return
        self.conversation.set_participants([item for item in self.conversation.participants if item != name])
        self._sync_select_options()
        self.save(silent=True)
        self.refresh_participants()
        self.refresh_prompt()

    def set_participant_url(self, name: str, url: str) -> None:
        self.conversation.set_participant_url(name, url)
        self.save(silent=True)

    def open_ai_url(self, name: str, silent: bool = False) -> bool:
        fallback_url = SUMMARY_AI_URL if name == "总结" else DEFAULT_PARTICIPANT_URLS.get(name, "")
        url = self._normalized_url(self.conversation.participant_urls.get(name) or fallback_url)
        return self.open_url(url, name, silent=silent)

    def open_url(self, url: str, target_name: str, silent: bool = False) -> bool:
        url = self._normalized_url(url)
        if not url:
            if not silent:
                ui.notify("先给这个 AI 粘贴网址。", type="warning")
            return False
        if not self._is_valid_url(url):
            ui.notify("这个网址看起来不对，请检查 AI 发言者里的网址。", type="warning")
            return False
        window_name = f"miao_ai_{self._safe_window_name(target_name)}"
        ui.run_javascript(f"window.open({json.dumps(url)}, {json.dumps(window_name)})")
        return True

    def _advance_prompt_target_after(self, speaker: str) -> None:
        next_name = self._next_unspoken_ai_in_round(speaker)
        self.prompt_ai_name = next_name
        self.import_ai_name = next_name
        self._sync_select_options()

    def _next_unspoken_ai_in_round(self, current_speaker: str) -> str:
        names = self.conversation.participants
        spoken = self._ai_spoken_since_last_user()
        for name in names:
            if name not in spoken:
                return name

        if current_speaker in names:
            index = names.index(current_speaker)
            return names[(index + 1) % len(names)]
        return names[0]

    def _ai_spoken_since_last_user(self) -> set[str]:
        spoken: set[str] = set()
        for message in reversed(self.conversation.messages):
            if message.role == "user":
                break
            if message.speaker in self.conversation.participants:
                spoken.add(message.speaker)
        return spoken

    def _speaker_color(self, speaker: str) -> tuple[str, str]:
        if speaker in SPEAKER_COLORS:
            return SPEAKER_COLORS[speaker]
        index = sum(ord(char) for char in speaker) % len(FALLBACK_COLORS)
        return FALLBACK_COLORS[index]

    def _display_speaker(self, message) -> str:
        if message.role == "user":
            return "我"
        return message.speaker

    def _download_filename(self, extension: str) -> str:
        title = "".join(char for char in self.conversation.title if char not in r'\/:*?"<>|').strip()
        safe_title = title or "miao_ai_discussion"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{safe_title}_{timestamp}.{extension}"

    def _topic_display_text(self) -> str:
        return self.conversation.title or "未设置讨论主题"

    def _normalized_url(self, url: str) -> str:
        cleaned = url.strip()
        if not cleaned:
            return ""
        if not urlparse(cleaned).scheme:
            cleaned = f"https://{cleaned}"
        return cleaned

    def _is_valid_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and "." in parsed.netloc

    def _safe_window_name(self, value: str) -> str:
        return "".join(char if char.isalnum() else "_" for char in value) or "default"

    def _save_file_with_picker(self, content: str, filename: str, mime_type: str) -> None:
        script = f"""
        (async () => {{
            const content = {json.dumps(content, ensure_ascii=False)};
            const filename = {json.dumps(filename, ensure_ascii=False)};
            const mimeType = {json.dumps(mime_type)};
            if (window.showSaveFilePicker) {{
                try {{
                    const handle = await window.showSaveFilePicker({{
                        suggestedName: filename,
                        types: [{{ description: 'Discussion file', accept: {{ [mimeType]: ['.' + filename.split('.').pop()] }} }}],
                    }});
                    const writable = await handle.createWritable();
                    await writable.write(new Blob([content], {{ type: mimeType + ';charset=utf-8' }}));
                    await writable.close();
                    return;
                }} catch (error) {{
                    if (error && error.name === 'AbortError') return;
                    console.warn(error);
                }}
            }}
            const blob = new Blob([content], {{ type: mimeType + ';charset=utf-8' }});
            const url = URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.download = filename;
            anchor.click();
            URL.revokeObjectURL(url);
        }})();
        """
        ui.run_javascript(script)
        ui.notify("已打开保存窗口；如果浏览器不支持，会改用下载。", type="positive")

    def _txt_text(self) -> str:
        lines = [
            f"讨论主题：{self.conversation.title or '无标题'}",
            f"讨论 ID：{self.conversation.conversation_id}",
            f"更新时间：{self.conversation.updated_at}",
            f"参与者：{', '.join(self.conversation.participants)}",
            "",
        ]
        for message in self.conversation.messages:
            speaker = self._display_speaker(message)
            lines.append(f"---")
            lines.append("")
            lines.append(f"{speaker}（{message.created_at}）：")
            lines.append("")
            lines.append(message.content)
            lines.append("")
        return "\n".join(lines)

    def _markdown_text(self) -> str:
        lines = [
            f"# {self.conversation.title}",
            "",
            f"- 讨论 ID：{self.conversation.conversation_id}",
            f"- 更新时间：{self.conversation.updated_at}",
            f"- AI：{', '.join(self.conversation.participants)}",
            "",
            "## Conversation History",
            "",
        ]
        for message in self.conversation.messages:
            speaker = self._display_speaker(message)
            lines.extend([f"### {speaker}（{message.created_at}）", "", message.content, ""])
        return "\n".join(lines)

    def _styles(self) -> None:
        ui.add_head_html(
            """
            <style>
            body {
                background: #f6f3ee;
                color: #1f2328;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
            .app-shell {
                width: 100%;
                max-width: 1500px;
                margin: 0 auto;
                padding: 8px 12px 16px;
                gap: 10px;
                min-height: 100vh;
            }
            .topbar {
                width: 100%;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
                padding: 10px 14px;
                border: 1px solid rgba(44, 62, 80, 0.12);
                border-radius: 10px;
                background: linear-gradient(135deg, #f8fbff 0%, #eef6ff 100%);
                box-shadow: 0 4px 20px rgba(33, 84, 122, 0.08);
                -webkit-app-region: drag;
            }
            .topbar .q-btn {
                -webkit-app-region: no-drag;
            }
            .title-block {
                gap: 0;
                padding-left: 2px;
            }
            .app-title {
                font-size: 26px;
                font-weight: 900;
                letter-spacing: 0;
                color: #123457;
                padding: 2px 0;
                text-shadow: 0 1px 0 rgba(255, 255, 255, 0.85);
            }
            .top-actions, .button-row {
                align-items: center;
                gap: 10px;
                flex-wrap: wrap;
            }
            .button-row {
                width: 100%;
                display: flex;
                gap: 10px;
            }
            .button-row .q-btn {
                flex: 1;
                flex-basis: 0;
                min-width: 0;
                height: 42px;
            }
            .button-row .q-btn .q-btn__content {
                justify-content: center;
                white-space: nowrap;
            }
            .main-grid {
                width: 100%;
                display: grid;
                grid-template-columns: minmax(220px, 300px) minmax(320px, 1fr) minmax(260px, 360px);
                gap: 10px;
                align-items: start;
            }
            .panel {
                background: rgba(255, 253, 248, 0.97);
                border: 1px solid rgba(31, 35, 40, 0.1);
                border-radius: 10px;
                box-shadow: 0 4px 20px rgba(32, 26, 18, 0.07);
                padding: 14px;
                position: relative;
                overflow: hidden;
            }
            .panel::before {
                content: "";
                position: absolute;
                top: 0; left: 0; right: 0;
                height: 3px;
                border-radius: 10px 10px 0 0;
            }
            .side-panel::before   { background: linear-gradient(90deg, #7c6df0, #a78bfa); }
            .history-panel::before { background: linear-gradient(90deg, #06b6d4, #67e8f9); }
            .right-panel::before  { background: linear-gradient(90deg, #f59e0b, #fcd34d); }
            .side-panel    { border-top: 3px solid transparent; }
            .history-panel { border-top: 3px solid transparent; }
            .right-panel   { border-top: 3px solid transparent; }
            .side-panel { gap: 10px; }
            .history-panel {
                min-height: calc(100vh - 150px);
                gap: 10px;
            }
            .history-scroll {
                flex: 1;
                width: 100%;
                min-height: 0;
                height: calc(100vh - 260px);
                max-height: calc(100vh - 260px);
                overflow-y: auto;
                padding-right: 4px;
            }
            .panel-head {
                align-items: center;
                justify-content: space-between;
                width: 100%;
            }
            .panel-title {
                font-size: 16px;
                font-weight: 800;
                color: #202428;
            }
            .small-title { margin-top: 2px; }
            .section-title-row {
                width: 100%;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
            }
            .subtle-label {
                font-size: 13px;
                font-weight: 700;
                color: #6b5f51;
            }
            .topic-row {
                width: 100%;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
                padding: 9px 10px;
                border: 1px solid rgba(31, 35, 40, 0.08);
                border-radius: 8px;
                background: #fffaf4;
            }
            .topic-display {
                color: #252a30;
                font-size: 14px;
                font-weight: 800;
                line-height: 1.4;
                overflow-wrap: anywhere;
            }
            .topic-edit {
                width: 100%;
                gap: 8px;
            }
            .hidden {
                display: none !important;
            }
            .count-pill {
                padding: 4px 10px;
                border-radius: 999px;
                background: #e6f0ff;
                color: #24508d;
                font-weight: 700;
                font-size: 12px;
            }
            .full { width: 100%; }
            .draft-box textarea, .reply-box textarea { min-height: 118px !important; }
            .prompt-box textarea {
                min-height: 330px !important;
                font-family: Consolas, "Microsoft YaHei", monospace;
                line-height: 1.55;
            }
            .soft-separator { margin: 4px 0; opacity: 0.55; }
            .participant-list {
                width: 100%;
                gap: 6px;
            }
            .participant-item {
                width: 100%;
                gap: 6px;
                padding: 8px 10px;
                border: 1px solid rgba(31, 35, 40, 0.08);
                border-radius: 8px;
                transition: box-shadow 0.15s;
            }
            .participant-item:hover {
                box-shadow: 0 3px 12px rgba(32, 26, 18, 0.09);
            }
            .participant-head {
                width: 100%;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
            }
            .participant-actions {
                gap: 4px;
                align-items: center;
            }
            .compact-btn {
                font-size: 12px !important;
                padding: 4px 12px !important;
                min-width: 0 !important;
                border-radius: 6px !important;
                font-weight: 600 !important;
            }
            .join-btn {
                background: #e8f5e9 !important;
                color: #2e7d32 !important;
                border: 1px solid #a5d6a7 !important;
            }
            .join-btn:hover {
                background: #c8e6c9 !important;
            }
            .api-tune-btn {
                color: #6b5f51 !important;
                opacity: 0.7;
            }
            .api-tune-btn:hover {
                opacity: 1 !important;
            }
            .api-setup-btn {
                background: #fff3e0 !important;
                color: #bf6007 !important;
                border: 1px solid #ffcc80 !important;
            }
            .api-setup-btn:hover {
                background: #ffe0b2 !important;
            }
            .participant-name {
                font-weight: 800;
                font-size: 13px;
                color: #24364d;
            }
            .status-icon {
                font-size: 12px;
                margin-left: 4px;
                opacity: 0.86;
                line-height: 1;
            }
            .api-badge {
                opacity: 0.8;
            }
            .round-tabs {
                width: 100%;
                gap: 6px;
                flex-wrap: wrap;
                align-items: center;
            }
            @keyframes fadeSlideIn {
                from { opacity: 0; transform: translateY(6px); }
                to   { opacity: 1; transform: translateY(0); }
            }
            .message-card { animation: fadeSlideIn 0.2s ease-out; }
            .participant-item { animation: fadeSlideIn 0.18s ease-out; }
            .round-tab {
                color: #18314f !important;
                background: #ffffff !important;
                border: 1.5px solid rgba(36, 80, 141, 0.35) !important;
                border-radius: 999px !important;
                font-weight: 800;
                font-size: 11px;
                min-width: 30px;
                padding: 2px 9px !important;
                transition: background 0.15s, color 0.15s, box-shadow 0.15s !important;
            }
            .active-round-tab {
                background: #1a3a6b !important;
                color: #ffffff !important;
                border-color: #1a3a6b !important;
                box-shadow: 0 2px 8px rgba(26, 58, 107, 0.3) !important;
            }
            .round-tab:hover:not(.active-round-tab) {
                background: #e8efff !important;
                box-shadow: 0 1px 4px rgba(36, 80, 141, 0.15) !important;
            }
            .round-list {
                width: 100%;
                gap: 14px;
            }
            .round-block {
                width: 100%;
                gap: 10px;
                padding-bottom: 2px;
            }
            .message-card {
                width: 100%;
                gap: 8px;
                padding: 12px 14px;
                border-radius: 8px;
                border: 1px solid rgba(31, 35, 40, 0.08);
                transition: box-shadow 0.15s, border-color 0.15s, transform 0.15s;
            }
            .message-card:hover {
                box-shadow: 0 4px 16px rgba(32, 26, 18, 0.1);
                border-color: rgba(31, 35, 40, 0.16);
                transform: translateY(-1px);
            }
            .message-meta {
                width: 100%;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
            }
            .speaker-row {
                align-items: center;
                gap: 8px;
                min-width: 0;
            }
            .message-meta-right {
                align-items: center;
                gap: 8px;
            }
            .delete-msg-btn {
                color: #9b4238 !important;
                opacity: 0.6;
            }
            .delete-msg-btn:hover {
                opacity: 1 !important;
            }
            .api-status-label {
                font-size: 12px;
                font-weight: 600;
            }
            .api-status-row {
                align-items: center;
                gap: 8px;
                min-height: 24px;
            }
            .configured-label {
                font-size: 12px;
                font-weight: 600;
                color: #1d7a46;
            }
            .muted-text {
                font-size: 12px;
                color: #8a7a6d;
            }
            .auto-mode-badge {
                font-size: 11px;
                font-weight: 700;
                background: #fff7d1;
                color: #8a6000;
                padding: 2px 8px;
                border-radius: 999px;
            }
            .speaker-dot {
                width: 10px;
                height: 10px;
                border-radius: 999px;
                display: inline-block;
                flex: 0 0 auto;
            }
            .speaker {
                font-size: 15px;
                font-weight: 800;
            }
            .time {
                font-size: 12px;
                color: #7b6f62;
                white-space: nowrap;
            }
            .message-content {
                line-height: 1.7;
                color: #252a30;
                word-break: break-word;
            }
            .message-content pre {
                background: #f4f1ec;
                padding: 8px 12px;
                border-radius: 6px;
                overflow-x: auto;
                font-size: 13px;
            }
            .message-content code {
                background: #f4f1ec;
                padding: 2px 5px;
                border-radius: 3px;
                font-size: 13px;
            }
            .message-content pre code {
                background: none;
                padding: 0;
            }
            .message-content blockquote {
                border-left: 3px solid #c5bfb4;
                padding-left: 12px;
                color: #6b5f51;
                margin: 8px 0;
            }
            .message-content ul, .message-content ol {
                padding-left: 20px;
                margin: 4px 0 8px;
            }
            .message-content li {
                margin: 2px 0;
            }
            .message-content table {
                border-collapse: collapse;
                width: 100%;
                margin: 8px 0;
            }
            .message-content th, .message-content td {
                border: 1px solid #d8d2c8;
                padding: 6px 10px;
                text-align: left;
            }
            .message-content th {
                background: #f4f1ec;
                font-weight: 700;
            }
            .message-content h1,
            .message-content h2,
            .message-content h3 {
                font-size: 16px;
                line-height: 1.45;
                margin: 8px 0 6px;
                font-weight: 800;
            }
            .message-content h4,
            .message-content h5,
            .message-content h6 {
                font-size: 15px;
                line-height: 1.45;
                margin: 8px 0 6px;
                font-weight: 800;
            }
            .message-content p { margin: 0 0 8px; }
            .collapsed-preview {
                mask-image: linear-gradient(180deg, #000 72%, transparent 100%);
            }
            .collapsible-message {
                width: 100%;
                gap: 6px;
            }
            .fold-btn {
                align-self: flex-start;
                color: #24508d !important;
                font-weight: 800;
                margin-left: -8px;
            }
            .empty-state {
                width: 100%;
                min-height: calc(100vh - 300px);
                align-items: center;
                justify-content: center;
                text-align: center;
                gap: 8px;
                color: #746657;
            }
            .empty-icon {
                font-size: 42px;
                color: #d08a2d;
            }
            .empty-title {
                font-size: 18px;
                font-weight: 800;
                color: #2d2a26;
            }
            .empty-copy {
                max-width: 320px;
                font-size: 14px;
            }
            .danger-ghost-btn {
                color: #9b4238 !important;
                border: 1px solid rgba(155, 66, 56, 0.3) !important;
            }
            .danger-ghost-btn:hover {
                background: rgba(155, 66, 56, 0.08) !important;
            }
            .window-ctrl-btn {
                color: #6b5f51 !important;
                font-size: 18px !important;
            }
            .window-ctrl-btn:hover {
                background: rgba(0,0,0,0.06) !important;
            }
            .window-close-btn {
                color: #c0392b !important;
                font-size: 18px !important;
            }
            .window-close-btn:hover {
                background: rgba(192,57,43,0.1) !important;
            }
            .danger-btn {
                background: #c0392b !important;
                color: #ffffff !important;
            }
            .url-dialog {
                width: min(520px, calc(100vw - 32px));
                gap: 14px;
                border-radius: 8px;
            }
            .prompt-template-dialog {
                width: min(760px, calc(100vw - 32px));
                gap: 10px;
                border-radius: 8px;
            }
            .template-box textarea {
                min-height: 108px !important;
                line-height: 1.5;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
            .dialog-actions {
                width: 100%;
                justify-content: flex-end;
                gap: 10px;
            }
            .template-control-row {
                width: 100%;
                justify-content: space-between;
                align-items: center;
                gap: 10px;
            }
            .template-button-group {
                gap: 8px;
                align-items: center;
                flex-wrap: wrap;
            }
            .dialog-actions .q-btn {
                border: 1px solid rgba(31, 35, 40, 0.14) !important;
                border-radius: 6px !important;
            }
            @media (max-width: 1000px) {
                .main-grid {
                    grid-template-columns: 1fr;
                }
                .history-panel {
                    min-height: auto;
                }
                .history-scroll {
                    height: 430px;
                    max-height: 430px;
                }
                .empty-state {
                    min-height: 280px;
                }
            }
            @media (max-width: 640px) {
                .topbar {
                    align-items: flex-start;
                }
                .button-row {
                    grid-template-columns: 1fr;
                }
            }
            </style>
            """
        )
