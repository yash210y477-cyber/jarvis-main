import {
  openChrome,
  openVSCode,
  openExplorer,
  openTerminal,
} from "../electron/electron";

export function executeAction(response) {
  if (!response?.success) return;

  switch (response.action) {
    case "open_app":
      switch (response.target) {
        case "chrome":
          openChrome();
          return;

        case "vscode":
          openVSCode();
          return;

        case "explorer":
          openExplorer();
          return;

        case "terminal":
          openTerminal();
          return;

        default:
          console.log("Unknown app:", response.target);
          return;
      }

    case "google_search":
      window.open(response.url, "_blank");
      return;

    case "open_website":
      window.open(response.url, "_blank");
      return;

    default:
      console.log("No action found.");
      return;
  }
}