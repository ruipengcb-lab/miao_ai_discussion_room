import sys
import os

# PyInstaller 打包后 sys.stderr/sys.stdout 可能为 None，修复 uvicorn 日志崩溃
if getattr(sys, 'frozen', False):
    class _DummyStream:
        def write(self, s): pass
        def flush(self): pass
        def isatty(self): return False
    if sys.stderr is None:
        sys.stderr = _DummyStream()
    if sys.stdout is None:
        sys.stdout = _DummyStream()

from nicegui import ui

from storage import load_conversation
from ui import DiscussionUI


def create_ui() -> None:
    # 启动时读取本地 JSON，确保上一次讨论能自动恢复。
    conversation = load_conversation()
    DiscussionUI(conversation).build()


def main() -> None:
    try:
        ui.run(
            root=create_ui,
            title="喵酱 AI 讨论室",
            host="0.0.0.0",
            port=8088,
            reload=False,
            language="zh-CN",
            native=False,
        )
    except KeyboardInterrupt:
        print("\n收到中断信号，喵酱讨论室已关闭。")


if __name__ in {"__main__", "__mp_main__"}:
    main()
