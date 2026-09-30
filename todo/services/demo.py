"""Launch the optional demo without ever touching the live shop database."""
from pathlib import Path
import os
import subprocess
import sys

def _app_root():
    return Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parents[2]

def launcher_path():
    return _app_root() / "TEST_TODO.bat"

def launch_demo():
    launcher=launcher_path()
    if not launcher.is_file():
        raise FileNotFoundError("Optional demo launcher is not installed.")
    if os.name=="nt":
        return subprocess.Popen(["cmd","/c",str(launcher)],cwd=str(launcher.parent))
    return subprocess.Popen([str(launcher)],cwd=str(launcher.parent))
