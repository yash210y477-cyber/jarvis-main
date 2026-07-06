import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export async function searchStoreApp(appName) {
  try {
    const psCommand =
      `Get-StartApps | ` +
      `Where-Object { $_.Name -like '*${appName}*' } | ` +
      `Select-Object -First 1 Name, AppID | ` +
      `ConvertTo-Json -Compress`;

    const { stdout, stderr } = await execAsync(
      `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "${psCommand}"`
    );

    if (stderr) {
      console.log("PowerShell Error:", stderr);
    }

    if (!stdout || !stdout.trim()) {
      return null;
    }

    console.log("PowerShell Output:", stdout);

    return JSON.parse(stdout);

  } catch (error) {
    console.error(error);
    return null;
  }
}