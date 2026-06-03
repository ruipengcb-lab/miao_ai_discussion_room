# 喵酱 AI 讨论室

一个多 AI 讨论工作台，支持配置不同 AI 角色、生成讨论提示词、保存对话记录，并提供 React + Electron 桌面版。

## 功能

- 多个 AI 角色参与同一场讨论
- 根据历史发言生成下一轮提示词
- 支持配置不同 AI 服务商和模型
- 保存讨论历史
- 提供 NiceGUI 版本和 React + Electron 桌面版

## 目录

- `backend/`：桌面版后端服务
- `frontend/`：React + Electron 桌面端
- `api_providers.py`：AI 服务商请求适配
- `conversation.py`：讨论消息数据结构
- `prompt_builder.py`：提示词生成
- `storage.py`：本地数据读写
- `ui.py`：NiceGUI 界面
- `main.py`：NiceGUI 入口

## 运行 NiceGUI 版本

```bat
pip install -r requirements.txt
python main.py
```

使用虚拟环境：

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 运行桌面版前端

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
