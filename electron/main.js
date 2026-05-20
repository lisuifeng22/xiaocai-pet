const { app, BrowserWindow, ipcMain } = require("electron");
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

ipcMain.on("drag-window", (_, { deltaX, deltaY }) => {
  if (!win) return;
  const [x, y] = win.getPosition();
  win.setPosition(x + deltaX, y + deltaY);
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
