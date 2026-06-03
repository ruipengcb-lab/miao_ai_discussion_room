# 喵酱 AI 讨论室

一个多 AI 讨论工作台，支持配置不同 AI 角色、生成讨论提示词、保存对话记录，并提供 React + Electron 桌面版。

## 目录说明

- `backend/`：桌面版后端服务。
- `frontend/`：React + Electron 桌面端。
- `api_providers.py`：不同 AI 服务商的请求适配。
- `conversation.py`：讨论消息数据结构。
- `prompt_builder.py`：根据历史消息生成提示词。
- `storage.py`：本地设置与对话存储。
- `ui.py`：NiceGUI 版本界面。
- `main.py`：NiceGUI 版本入口。

## 运行 NiceGUI 版本

```bat
pip install -r requirements.txt
python main.py
```

如果使用虚拟环境，可以先创建并激活：

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 运行 React + Electron 桌面版

```bat
cd frontend
npm install
npm start
```

另开一个终端：

```bat
cd frontend
npm run electron
```

## 打包

打包 NiceGUI 版本：

```bat
build_exe.bat
```

打包前后端一体化桌面版：

```bat
build_all.bat
```

打包产物会生成在 `dist/` 或 `frontend/release/`，这些目录属于本地构建结果，不提交到 GitHub。

## 注意

- `data/` 保存本地对话和设置，不提交到 GitHub。
- `.venv/`、`build/`、`dist/`、`frontend/node_modules/`、`frontend/release/` 都是本地生成目录，不提交到 GitHub。
- API Key 请只保存在本地设置中，不要写进源码。
