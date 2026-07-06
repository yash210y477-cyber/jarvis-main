const electron = window.electron;

export async function openApplication(appName) {
  if (!electron) return false;

  return await electron.openApplication(appName);
}

export async function getSystemInfo() {
  if (!electron) return null;

  return await electron.getSystemInfo();
}