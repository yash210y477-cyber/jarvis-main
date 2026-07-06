import { app, BrowserWindow, ipcMain } from "electron";
import path from "path";
import { fileURLToPath } from "url";
import si from "systeminformation";

import { APP_COMMANDS } from "./apps.js";
import {
  openApplication,
} from "./appDiscovery.js";

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

app.whenReady().then(() => {
  createWindow();

  // ===========================
  // Universal App Launcher
  // ===========================

  ipcMain.handle("open-application", async (_, appName) => {
    if (!appName) return false;

    const command =
      APP_COMMANDS[appName.toLowerCase().trim()];

    if (!command) {
      console.log(`Unknown application: ${appName}`);
      return false;
    }

    return await openApplication(appName, APP_COMMANDS);
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

console.log(await searchInPath("chrome"));
console.log(await searchInPath("python"));
console.log(await searchInPath("git"));