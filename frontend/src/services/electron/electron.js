const electron = window.electron;

// ----------------------------
// Open Application
// ----------------------------
export async function openApplication(appName) {

  // Electron
  if (electron?.openApplication) {
    return await electron.openApplication(appName);
  }

  // Browser (localhost)
  try {

    const response = await fetch(
      `http://127.0.0.1:8000/open-app/${appName}`,
      {
        method: "POST",
      }
    );

    return await response.json();

  } catch (err) {
    console.error(err);

    return {
      success: false,
      error: err.message,
    };
  }
}


// ----------------------------
// System Information
// ----------------------------
export async function getSystemInfo() {

  // Electron
  if (electron?.getSystemInfo) {
    return await electron.getSystemInfo();
  }

  // Browser (localhost)
  try {

    const response = await fetch(
      "http://127.0.0.1:8000/system-info"
    );

    if (!response.ok) {
      throw new Error("Failed to fetch system info");
    }

    return await response.json();

  } catch (err) {

    console.error(err);

    return {
      cpu: 0,
      ram: 0,
      storage: 0,
      network: "Offline",
    };
  }
}