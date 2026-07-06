import { APP_COMMANDS } from "./apps.js";
import { launch, launchExecutable } from "./launcher.js";
import { searchInPath } from "./pathSearch.js";
import { searchStartMenu } from "./startMenuSearch.js";

export async function openApplication(appName) {
  if (!appName) {
    return false;
  }

  const keyword = appName.toLowerCase().trim();

  // =========================
  // 1. Known Applications
  // =========================

  if (APP_COMMANDS[keyword]) {
    return await launch(APP_COMMANDS[keyword]);
  }

  // =========================
  // 2. Search in PATH
  // =========================

  const executable = await searchInPath(keyword);

  if (executable) {
    return await launchExecutable(executable);
  }

  // =========================
  // 3. Search Start Menu
  // =========================

  const shortcut = searchStartMenu(keyword);

  if (shortcut) {
    return await launchExecutable(shortcut);
  }

  // =========================
  // 4. Not Found
  // =========================

  console.log(`Application not found: ${appName}`);

  return false;
}