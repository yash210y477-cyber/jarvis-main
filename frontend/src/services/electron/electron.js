const electron = window.electron;

export function openChrome() {
  return electron?.openChrome();
}

export function openVSCode() {
  return electron?.openVSCode();
}

export function openExplorer() {
  return electron?.openExplorer();
}

export function openTerminal() {
  return electron?.openTerminal();
}

export async function getSystemInfo() {
  if (!electron) return null;

  return await electron.getSystemInfo();
}