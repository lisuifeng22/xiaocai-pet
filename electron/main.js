const { app, BrowserWindow, ipcMain, screen } = require("electron");
const path = require("path");
const { exec } = require("child_process");

let win;
let dragState = null;

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

  win.on("closed", () => {
    exec("taskkill /F /IM python.exe", () => {});
  });
}

ipcMain.on("drag-window-start", (_, { mouseX, mouseY, petOffset }) => {
  if (!win || !Number.isFinite(mouseX) || !Number.isFinite(mouseY)) return;

  try {
    const [x, y] = win.getPosition();

    dragState = {
      startMouseX: Math.round(mouseX),
      startMouseY: Math.round(mouseY),
      startWinX: x,
      startWinY: y,
      petOffset: Number.isFinite(petOffset) ? Math.round(petOffset) : 0,
      lastX: x,
      lastY: y
    };
  } catch (_) {}
});

ipcMain.on("drag-window-move", (_, { mouseX, mouseY }) => {
  if (!win || !dragState || !Number.isFinite(mouseX) || !Number.isFinite(mouseY)) return;

  try {
    const [w, h] = win.getSize();

    const nextX = dragState.startWinX + Math.round(mouseX - dragState.startMouseX);
    const nextY = dragState.startWinY + Math.round(mouseY - dragState.startMouseY);

    const display = screen.getDisplayNearestPoint({
      x: nextX + w / 2,
      y: nextY + h / 2
    });

    const topBound = display.bounds.y - dragState.petOffset;
    const bottomBound = display.workArea.y + display.workArea.height - h;
    const clampedY = Math.max(topBound, Math.min(bottomBound, nextY));

    if (nextX === dragState.lastX && clampedY === dragState.lastY) return;

    dragState.lastX = nextX;
    dragState.lastY = clampedY;

    win.setPosition(nextX, clampedY);
  } catch (_) {}
});

ipcMain.on("drag-window-end", () => {
  dragState = null;
});

ipcMain.on("close-window", () => {
  exec("taskkill /F /IM python.exe", () => {});
  if (win) win.close();
});

ipcMain.on("set-window-shape", (_, regions) => {
  if (!win) return;
  try {
    win.setShape(regions);
  } catch (_) {}
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