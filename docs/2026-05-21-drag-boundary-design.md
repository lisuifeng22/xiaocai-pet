# 拖拽边界限制 — 设计文档

## 需求

移动宠物窗口时，人物位置不能超出屏幕顶端和底部，左右无限制。

## 设计

在 Electron 主进程 `drag-window` IPC 处理器中夹紧 Y 坐标。

### 边界规则

- **顶部**：窗口上沿贴到显示器物理上沿（`display.bounds.y`）
- **底部**：窗口下沿不盖住任务栏（`display.workArea.y + display.workArea.height - winHeight`）
- **左右**：不做任何限制

### 实现位置

只改 `electron/main.js`，`ipcMain.on("drag-window")` 回调。

### 伪代码

```
on drag-window(deltaX, deltaY):
  if no window, return
  [x, y] = win.getPosition()
  [w, h] = win.getSize()

  display = screen.getDisplayNearestPoint({ x: x + w/2, y: y + h/2 })
  topBound = display.bounds.y
  bottomBound = display.workArea.y + display.workArea.height - h

  newX = x + deltaX
  newY = clamp(y + deltaY, topBound, bottomBound)
  win.setPosition(newX, newY)
```

### 依赖

使用 Electron 内置 `screen` 模块，无需新增依赖。
