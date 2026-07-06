const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electron", {
  // Universal App Launcher
  openApplication: (appName) =>
    ipcRenderer.invoke("open-application", appName),

  // System Information
  getSystemInfo: () =>
    ipcRenderer.invoke("system-info"),
});