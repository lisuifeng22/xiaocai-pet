const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  platform: process.platform,
  dragWindow: (deltaX, deltaY, petOffset) => ipcRenderer.send("drag-window", { deltaX, deltaY, petOffset }),
  closeWindow: () => ipcRenderer.send("close-window")
});
