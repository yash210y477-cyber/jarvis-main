from tools.launcher import WindowsLauncher

launcher = WindowsLauncher()


def open_app(app_name: str):

    success, message = launcher.open(app_name)

    return {
        "success": success,
        "action": "open_app",
        "target": app_name,
        "message": message
    }


def close_app(app_name: str):

    success, message = launcher.close(app_name)

    return {
        "success": success,
        "action": "close_app",
        "target": app_name,
        "message": message
    }