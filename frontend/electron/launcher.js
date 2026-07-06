import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export async function launch(command) {

  try {

    await execAsync(command);

    return true;

  } catch {

    return false;

  }

}

export async function launchExecutable(path) {

  try {

    await execAsync(`start "" "${path}"`);

    return true;

  } catch {

    return false;

  }

}