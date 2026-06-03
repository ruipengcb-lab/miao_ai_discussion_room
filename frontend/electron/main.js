const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn, execFile } = require('child_process');

const isDev = !app.isPackaged;

let backendProc = null;

function getBackendExePath() {
  if (isDev) {
    // 开发模式：后端 exe 在项目根 dist 目录
    return path.join(__dirname, '..', '..', 'dist', 'miao-backend', 'miao-backend.exe');
  }
  // 打包后：后端 exe 在 resources/backend/ 目录
  return path.join(process.resourcesPath, 'backend', 'miao-backend.exe');
}

function startBackend() {
  const backendPath = getBackendExePath();
  console.log('Starting backend:', backendPath);

  backendProc = execFile(backendPath, [], {
    windowsHide: false,
    cwd: path.dirname(backendPath),
  });

  backendProc.stdout?.on('data', (data) => {
    console.log('[backend]', data.toString().trim());
  });
  backendProc.stderr?.on('data', (data) => {
    console.error('[backend]', data.toString().trim());
  });
  backendProc.on('exit', (code) => {
    console.log('[backend] exited with code', code);
    backendProc = null;
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 500,
    title: '多 AI 讨论工具',
    icon: path.join(__dirname, '..', '..', 'icon.ico'),
    frame: false,
    backgroundColor: '#f5f5f7',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  win.setMenuBarVisibility(false);

  // 窗口拖拽支持
  win.webContents.on('did-finish-load', () => {
    win.webContents.insertCSS(`
      .app { -webkit-app-region: drag; }
      input, textarea, select, button, .message-list, .sidebar, .prompt-panel, .modal-overlay, .round-tabs, .dropdown-menu { -webkit-app-region: no-drag; }
    `);
  });

  if (isDev) {
    // 开发模式：前端连 React dev server，后端连本地 API
    win.loadURL('http://localhost:3000');
  } else {
    // 打包模式：先启动后端，等它就绪后加载静态前端
    startBackend();
    waitForBackend(win);
  }

  ipcMain.on('minimize', () => win.minimize());
  ipcMain.on('maximize', () => win.isMaximized() ? win.unmaximize() : win.maximize());
  ipcMain.on('close', () => win.close());
}

function loadFrontend(win) {
  // 打包后通过后端 serve 前端（避免 file:// 路径问题导致白屏）
  win.loadURL('http://127.0.0.1:8765');
}

function waitForBackend(win) {
  const http = require('http');
  const maxAttempts = 30;
  let attempt = 0;

  function tryConnect() {
    attempt++;
    const req = http.get('http://127.0.0.1:8765/api/conversation', (res) => {
      res.resume(); // 丢弃响应体
      loadFrontend(win);
    });
    req.on('error', () => {
      if (attempt < maxAttempts) {
        setTimeout(tryConnect, 500);
      } else {
        loadFrontend(win);
      }
    });
    req.setTimeout(2000, () => {
      req.destroy();
      if (attempt < maxAttempts) {
        setTimeout(tryConnect, 500);
      } else {
        loadFrontend(win);
      }
    });
  }
  tryConnect();
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (backendProc) {
    backendProc.kill();
    backendProc = null;
  }
  app.quit();
});

app.on('before-quit', () => {
  if (backendProc) {
    backendProc.kill();
    backendProc = null;
  }
});
