import os
import winreg
import shutil
import subprocess
from pathlib import Path


START_MENU_DIRS = [
    Path(os.environ.get("ProgramData", r"C:\ProgramData"))
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs",

    Path(os.environ.get("APPDATA", ""))
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs",
]


PROGRAM_DIRS = [

    Path(os.environ.get("ProgramFiles", r"C:\Program Files")),

    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),

    Path(os.environ.get("LOCALAPPDATA", "")),

]


ALIASES = {

    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",

    "terminal": "cmd",
    "command prompt": "cmd",

    "calculator": "calc",

    "file explorer": "explorer",

    "google chrome": "chrome",

}


class WindowsLauncher:

    def normalize(self, name: str):

        return ALIASES.get(
            name.lower().strip(),
            name.strip()
        )


    def search_path(self, app):

        exe = shutil.which(app)

        if exe:
            return exe

        return None


    def search_registry(self, app):

        roots = [

            winreg.HKEY_LOCAL_MACHINE,
            winreg.HKEY_CURRENT_USER,

        ]

        keys = [

            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",

            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths",

        ]

        names = [

            app,

            app + ".exe"

        ]

        for root in roots:

            for key in keys:

                for exe in names:

                    try:

                        reg = winreg.OpenKey(
                            root,
                            key + "\\" + exe
                        )

                        value, _ = winreg.QueryValueEx(
                            reg,
                            ""
                        )

                        if os.path.exists(value):
                            return value

                    except Exception:
                        pass

        return None
    
    def search_start_menu(self, app):

        target = app.lower()

        for root in START_MENU_DIRS:

            if not root.exists():
                continue

            try:

                for item in root.rglob("*"):

                    if item.suffix.lower() not in (
                        ".lnk",
                        ".exe",
                        ".url"
                    ):
                        continue

                    if target in item.stem.lower():

                        return str(item)

            except Exception:
                pass

        return None


    def search_program_files(self, app):

        target = app.lower()

        for root in PROGRAM_DIRS:

            if not root.exists():
                continue

            try:

                for exe in root.rglob("*.exe"):

                    name = exe.stem.lower()

                    if (
                        target == name
                        or target in name
                        or name in target
                    ):

                        return str(exe)

            except Exception:
                pass

        return None


    def find_application(self, app):

        app = self.normalize(app)

        path = self.search_path(app)

        if path:
            return path

        path = self.search_registry(app)

        if path:
            return path

        path = self.search_start_menu(app)

        if path:
            return path

        path = self.search_program_files(app)

        if path:
            return path

        return None
    def open(self, app):

        app = self.normalize(app)

        target = self.find_application(app)

        if target is None:

            return (
                False,
                f"Application '{app}' not found."
            )

        try:

            if target.lower().endswith(".lnk"):

                os.startfile(target)

            elif target.lower().endswith(".url"):

                os.startfile(target)

            elif target.lower().endswith(".exe"):

                subprocess.Popen(
                    [target],
                    shell=False
                )

            else:

                subprocess.Popen(
                    target,
                    shell=True
                )

            return (
                True,
                f"{app} opened successfully."
            )

        except Exception as e:

            return (
                False,
                str(e)
            )


    def close(self, app):

        app = self.normalize(app)

        exe = app

        path = self.find_application(app)

        if path:

            exe = Path(path).name

        if not exe.lower().endswith(".exe"):

            exe += ".exe"

        try:

            subprocess.run(

                [
                    "taskkill",
                    "/F",
                    "/IM",
                    exe
                ],

                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL

            )

            return (

                True,
                f"{app} closed successfully."

            )

        except Exception as e:

            return (

                False,
                str(e)

            )
    