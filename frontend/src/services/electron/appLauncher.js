const electron = window.electron;

export async function openApplication(appName) {
  if (!electron) return false;

  return await electron.openApplication(appName);
}