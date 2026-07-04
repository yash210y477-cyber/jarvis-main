import { app, BrowserWindow, ipcMain } from "electron";
import { exec } from "child_process";
import path from "path";
import { fileURLToPath } from "url";
import si from "systeminformation";

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

  ipcMain.handle("open-chrome", () => exec("start chrome"));
  ipcMain.handle("open-vscode", () => exec("code"));
  ipcMain.handle("open-explorer", () => exec("explorer"));
  ipcMain.handle("open-terminal", () => exec("start cmd"));

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

      network: network.some((n) => n.operstate === "up")
        ? "Online"
        : "Offline",
    };
  });
});