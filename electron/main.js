const { app, BrowserWindow, ipcMain, screen } = require("electron");
const path = require("path");

let win;

function createWindow() {
  win = new BrowserWindow({
    width: 280,
    height: 480,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: false,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  win.loadFile(path.join(__dirname, "../frontend/index.html"));
  win.setAlwaysOnTop(true, "screen-saver");
}

ipcMain.on("drag-window", (_, { deltaX, deltaY, petOffset }) => {
  if (!win || typeof petOffset !== "number") return;
  try {
    const [x, y] = win.getPosition();
    const [w, h] = win.getSize();
    const display = screen.getDisplayNearestPoint({ x: x + w / 2, y: y + h / 2 });
    const topBound = display.bounds.y - petOffset;
    const bottomBound = display.workArea.y + display.workArea.height - h;
    win.setPosition(x + deltaX, Math.max(topBound, Math.min(bottomBound, y + deltaY)));
  } catch (_) {}
});

ipcMain.on("close-window", () => {
  if (win) win.close();
});

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
