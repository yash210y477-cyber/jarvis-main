import { app, BrowserWindow, ipcMain } from "electron";
import path from "path";
import { fileURLToPath } from "url";
import si from "systeminformation";

import { openApplication } from "./appDiscovery.js";
import { buildApplicationIndex } from "./indexBuilder.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1700,
    height: 950,
    backgroundColor: "#070B14",
    autoHideMenuBar: true,

    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadURL("http://localhost:5173");
}

app.whenReady().then(async () => {
  // ===========================
  // Build Application Index
  // ===========================

  await buildApplicationIndex();

  // ===========================
  // Create Window
  // ===========================

  createWindow();

  // ===========================
  // Universal App Launcher
  // ===========================

  ipcMain.handle("open-application", async (_, appName) => {
    return await openApplication(appName);
  });

  // ===========================
  // System Information
  // ===========================

  ipcMain.handle("system-info", async () => {
    const cpu = await si.currentLoad();
    const memory = await si.mem();
    const disks = await si.fsSize();
    const network = await si.networkInterfaces();

    return {
      cpu: Math.round(cpu.currentLoad),

      ram: Math.round(
        (memory.active / memory.total) * 100
      ),

      storage:
        disks.length > 0
          ? Math.round(disks[0].use)
          : 0,

      network: network.some(
        (n) => n.operstate === "up"
      )
        ? "Online"
        : "Offline",
    };
  });
});

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


