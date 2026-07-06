import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export async function searchInPath(appName) {
  try {
    const { stdout } = await execAsync(`where ${appName}`);

    if (!stdout.trim()) {
      return null;
    }

    const paths = stdout
      .split(/\r?\n/)
      .map((path) => path.trim())
      .filter(Boolean);

    return paths.length > 0 ? paths[0] : null;
  } catch {
    return null;
  }
}