"""
极简桌面启动器 - 打包成独立 exe（双击即用，无黑窗口）
功能：启动 NiceGUI 后端，用 Edge --app 模式打开无边框桌面窗口

onedir 模式打包（推荐）：
  pyinstaller --onedir --windowed --name MiaoAIDiscussionRoom launcher.py

onefile 模式打包：
  pyinstaller --onefile --windowed --name MiaoAIDiscussionRoom launcher.py
"""
import sys
import os
import time
import subprocess
import socket

APP_NAME = "喵酱 AI 讨论室"
PORT = 8088
BACKEND_SCRIPT = "main.py"
MAIN_SUBDIR = "app"


def port_is_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except (socket.error, OSError):
        return False


def wait_for_server(port: int, timeout: int = 20) -> bool:
    for _ in range(timeout):
        if port_is_open(port):
            return True
        time.sleep(1)
    return False


def get_app_dir() -> str:
    """获取应用根目录（与 exe 同级）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def find_main_py(app_dir: str) -> str | None:
    """在多个可能的位置找 main.py"""
    # 1. 同目录
    p = os.path.join(app_dir, BACKEND_SCRIPT)
    if os.path.exists(p):
        return p
    # 2. app/ 子目录（onedir 打包结构）
    p = os.path.join(app_dir, MAIN_SUBDIR, BACKEND_SCRIPT)
    if os.path.exists(p):
        return p
    # 3. 上一级
    p = os.path.join(app_dir, "..", BACKEND_SCRIPT)
    if os.path.exists(p):
        return os.path.normpath(p)
    return None


def get_python_exe() -> str:
    """获取 Python 解释器路径"""
    if getattr(sys, 'frozen', False):
        app_dir = get_app_dir()
        py_exe = os.path.join(app_dir, "python.exe")
        if os.path.exists(py_exe):
            return py_exe
        py3_exe = os.path.join(app_dir, "python3.exe")
        if os.path.exists(py3_exe):
            return py3_exe
    return sys.executable


def find_edge_path() -> str | None:
    """查找 Edge 可执行文件路径"""
    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def open_desktop_window(url: str) -> bool:
    """用 Edge --app 模式打开无边框桌面窗口"""
    edge_path = find_edge_path()
    if edge_path:
        subprocess.Popen([
            edge_path,
            f"--app={url}",
            "--start-maximized",
            "--no-first-run",
        ])
        return True
    # 没有 Edge，回退到默认浏览器
    import webbrowser
    webbrowser.open(url)
    return False


def start_backend(main_py_path: str) -> subprocess.Popen | None:
    python_exe = get_python_exe()
    work_dir = os.path.dirname(main_py_path) or "."
    try:
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        proc = subprocess.Popen(
            [python_exe, main_py_path],
            cwd=work_dir,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        return proc
    except Exception as e:
        print(f"[启动失败] {e}")
        return None


def main():
    app_dir = get_app_dir()
    main_py = find_main_py(app_dir)

    if main_py is None:
        print(f"[错误] 找不到 {BACKEND_SCRIPT}")
        print(f"[提示] 请确保 {BACKEND_SCRIPT} 在以下位置之一：")
        print(f"  - {app_dir}")
        print(f"  - {os.path.join(app_dir, MAIN_SUBDIR)}")
        time.sleep(5)
        sys.exit(1)

    url = f"http://127.0.0.1:{PORT}"

    if port_is_open(PORT):
        print(f"[{APP_NAME}] 服务已经在运行，直接打开窗口...")
        open_desktop_window(url)
        return

    print(f"[{APP_NAME}] 正在启动服务...")
    proc = start_backend(main_py)
    if proc is None:
        time.sleep(5)
        sys.exit(1)

    if not wait_for_server(PORT, timeout=20):
        print(f"[错误] 服务启动超时（20秒）")
        proc.terminate()
        sys.exit(1)

    print(f"[{APP_NAME}] 服务就绪，正在打开桌面窗口...")
    time.sleep(0.5)
    open_desktop_window(url)

    # 等待后端退出
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()
