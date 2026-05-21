const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  platform: process.platform,

  dragWindowStart: (mouseX, mouseY, petOffset) =>
    ipcRenderer.send("drag-window-start", { mouseX, mouseY, petOffset }),

  dragWindowMove: (mouseX, mouseY) =>
    ipcRenderer.send("drag-window-move", { mouseX, mouseY }),

  dragWindowEnd: () =>
    ipcRenderer.send("drag-window-end"),

  closeWindow: () => ipcRenderer.send("close-window"),

  setShape: (regions) => ipcRenderer.send("set-window-shape", regions)
});