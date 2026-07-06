import { APP_COMMANDS } from "./apps.js";

import { getApplication } from "./appIndex.js";

import { launch, launchExecutable } from "./launcher.js";

import { searchStoreApp } from "./appsFolderSearch.js";

import { launchStoreApp } from "./storeLauncher.js";

export async function openApplication(appName) {

    if (!appName)
        return false;

    const keyword = appName
        .toLowerCase()
        .trim();

    // ==================================
    // 1. Known Applications
    // ==================================

    if (APP_COMMANDS[keyword]) {

        return await launch(
            APP_COMMANDS[keyword]
        );

    }

    // ==================================
    // 2. Indexed Applications
    // ==================================

    const application =
        getApplication(keyword);

    if (application) {

        return await launchExecutable(
            application
        );

    }

    // ==================================
    // 3. Microsoft Store Apps
    // ==================================

    const storeApp =
        await searchStoreApp(appName);

    if (storeApp?.AppID) {

        return await launchStoreApp(
            storeApp.AppID
        );

    }

    // ==================================
    // 4. Not Found
    // ==================================

    console.log(
        `Application not found : ${appName}`
    );

    return false;

}