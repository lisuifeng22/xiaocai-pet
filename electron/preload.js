const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  platform: process.platform,
  dragWindow: (deltaX, deltaY) => ipcRenderer.send("drag-window", { deltaX, deltaY }),
  closeWindow: () => ipcRenderer.send("close-window")
});
