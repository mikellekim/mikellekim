"""Launch-at-login helpers for tray_app.py, one implementation per OS:

- macOS: a LaunchAgent plist in ~/Library/LaunchAgents
- Windows: a Run value under HKEY_CURRENT_USER (via winreg)
- Linux: an XDG autostart .desktop file in ~/.config/autostart

All three just re-run `<python> tray_app.py <same args>` at login, so
launch-at-login preserves whatever --hotkey/--model/--cleanup you were
using.
"""

import platform
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

APP_NAME = "wispr-flow-clone"
TRAY_SCRIPT = Path(__file__).resolve().parent / "tray_app.py"


def _command(extra_args: Optional[List[str]]) -> List[str]:
    return [sys.executable, str(TRAY_SCRIPT), *(extra_args or [])]


# ---- macOS: LaunchAgent plist ----

def _macos_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"com.{APP_NAME}.plist"


def _macos_enable(extra_args: Optional[List[str]]) -> Path:
    import plistlib

    plist_path = _macos_plist_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": f"com.{APP_NAME}",
        "ProgramArguments": _command(extra_args),
        "RunAtLoad": True,
        "KeepAlive": False,
    }
    with open(plist_path, "wb") as f:
        plistlib.dump(plist, f)
    subprocess.run(["launchctl", "load", str(plist_path)], check=False)
    return plist_path


def _macos_disable() -> Path:
    plist_path = _macos_plist_path()
    if plist_path.exists():
        subprocess.run(["launchctl", "unload", str(plist_path)], check=False)
        plist_path.unlink()
    return plist_path


def _macos_is_enabled() -> bool:
    return _macos_plist_path().exists()


# ---- Windows: HKCU Run key ----

_WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _windows_enable(extra_args: Optional[List[str]]) -> str:
    import winreg

    command = " ".join(f'"{part}"' for part in _command(extra_args))
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WINDOWS_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
    return command


def _windows_disable() -> None:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WINDOWS_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass


def _windows_is_enabled() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WINDOWS_RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except FileNotFoundError:
        return False


# ---- Linux: XDG autostart .desktop file ----

def _linux_desktop_path() -> Path:
    return Path.home() / ".config" / "autostart" / f"{APP_NAME}.desktop"


def _linux_enable(extra_args: Optional[List[str]]) -> Path:
    desktop_path = _linux_desktop_path()
    desktop_path.parent.mkdir(parents=True, exist_ok=True)
    exec_line = " ".join(_command(extra_args))
    desktop_path.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        f"Exec={exec_line}\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
    return desktop_path


def _linux_disable() -> Path:
    desktop_path = _linux_desktop_path()
    if desktop_path.exists():
        desktop_path.unlink()
    return desktop_path


def _linux_is_enabled() -> bool:
    return _linux_desktop_path().exists()


_BACKENDS = {
    "Darwin": (_macos_enable, _macos_disable, _macos_is_enabled),
    "Windows": (_windows_enable, _windows_disable, _windows_is_enabled),
    "Linux": (_linux_enable, _linux_disable, _linux_is_enabled),
}


def _backend():
    system = platform.system()
    if system not in _BACKENDS:
        raise RuntimeError(f"Launch-at-login isn't supported on {system!r}")
    return _BACKENDS[system]


def enable(extra_args: Optional[List[str]] = None):
    """Register tray_app.py to launch at login, re-run with extra_args."""
    enable_fn, _, _ = _backend()
    return enable_fn(extra_args)


def disable():
    """Remove the launch-at-login registration, if any."""
    _, disable_fn, _ = _backend()
    return disable_fn()


def is_enabled() -> bool:
    _, _, is_enabled_fn = _backend()
    return is_enabled_fn()
