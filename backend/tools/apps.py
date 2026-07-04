SUPPORTED_APPS = {
    "chrome": "chrome",
    "google chrome": "chrome",

    "vs code": "vscode",
    "visual studio code": "vscode",
    "code": "vscode",

    "explorer": "explorer",
    "file explorer": "explorer",

    "terminal": "terminal",
    "cmd": "terminal",
    "command prompt": "terminal",
}


def normalize_app_name(app_name: str) -> str:
    app_name = app_name.lower().strip()
    return SUPPORTED_APPS.get(app_name, app_name)


def open_app(app_name: str):

    app = normalize_app_name(app_name)

    return {
        "success": True,
        "action": "open_app",
        "target": app,
        "message": f"Opening {app}"
    }


def close_app(app_name: str):

    app = normalize_app_name(app_name)

    return {
        "success": True,
        "action": "close_app",
        "target": app,
        "message": f"Closing {app}"
    }