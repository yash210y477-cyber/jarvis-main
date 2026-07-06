import { APP_COMMANDS } from "./apps.js";
import { addApplication } from "./appIndex.js";
import { searchInPath } from "./pathSearch.js";
import { searchStartMenu } from "./startMenuSearch.js";

export async function buildApplicationIndex() {

  console.log("Building Application Index...");

  const apps = Object.keys(APP_COMMANDS);

  for (const app of apps) {

    // Skip aliases like "vs code", "google chrome"
    if (app.includes(" "))
      continue;

    let location = await searchInPath(app);

    if (!location) {
      location = searchStartMenu(app);
    }

    if (location) {
      addApplication(app, location);

      console.log(`Indexed: ${app}`);
    }

  }

  console.log("Application Index Ready");
}