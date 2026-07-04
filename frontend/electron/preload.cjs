const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electron", {
  openChrome: () => ipcRenderer.invoke("open-chrome"),

  openVSCode: () => ipcRenderer.invoke("open-vscode"),

  openExplorer: () => ipcRenderer.invoke("open-explorer"),

  openTerminal: () => ipcRenderer.invoke("open-terminal"),

  getSystemInfo: () => ipcRenderer.invoke("system-info"),
});