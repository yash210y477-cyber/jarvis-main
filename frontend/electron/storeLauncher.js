import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export async function launchStoreApp(appId) {
  try {
    const command = `start "" "shell:AppsFolder\\${appId}"`;

    console.log("Launching Store App:", command);

    await execAsync(command, {
      shell: "cmd.exe",
    });

    return true;

  } catch (error) {
    console.error("Store Launch Error:", error);

    return false;
  }
}