import { openApplication } from "../electron/electron";

export function executeAction(response) {
  if (!response?.success) return;

  switch (response.action) {
    case "open_app":
      openApplication(response.target);
      return;

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