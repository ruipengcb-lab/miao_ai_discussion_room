# 喵酱 AI 讨论室

一个 Python + NiceGUI 的半自动多人 AI 讨论原型。

## 运行

```bat
cd C:\Users\ruipe\CodeGeeXProjects\miao_ai_discussion_room
pip install -r requirements.txt
python main.py
```

如果你使用虚拟环境，先激活虚拟环境后再执行上面的命令。
当前 Codex 命令行里没有可用的 `python`/`py` 命令，旧 `.venv` 也指向了不存在的 Python 路径；如果你本机 VS Code 里有正常解释器，直接选那个解释器运行即可。

## 当前流程

1. 在界面里输入讨论主题和用户发言。
2. 工具保存完整 conversation history。
3. 选择目标 AI，生成并复制 Prompt。
4. 手动粘贴到 AI 网页。
5. 把 AI 返回内容粘回工具。
6. 选择发言者，点击“加入讨论”。
7. 下一轮 Prompt 会自动包含之前所有发言。

## 文件说明

- `main.py`：启动 NiceGUI。
- `ui.py`：界面和交互。
- `conversation.py`：统一管理 history。
- `prompt_builder.py`：根据 history 生成提示词。
- `storage.py`：保存、读取、导出讨论。
- `data/current_conversation.json`：运行后自动生成的当前讨论数据。

## 打包

```bat
build_exe.bat
```

打包结果在 `dist\MiaoAIDiscussionRoom\MiaoAIDiscussionRoom.exe`。
