#!/usr/bin/env python3
"""
Menu-bar / system-tray wrapper around flow.py's push-to-talk dictation.

Runs the same local, free dictation engine in the background and shows a
tray icon that reflects status (idle / recording / transcribing), with a
menu showing the active hotkey/model/cleanup settings and a Quit item.

Accepts the same flags as flow.py, e.g.:

    python tray_app.py --hotkey right_ctrl --model small --cleanup ollama
"""

import threading

import pystray
from PIL import Image, ImageDraw
from pynput import keyboard

from flow import Dictation, KEY_ALIASES, parse_args

ICON_SIZE = 64
STATE_COLORS = {
    "idle": (130, 130, 130, 255),
    "recording": (220, 50, 50, 255),
    "transcribing": (230, 160, 30, 255),
}


def make_icon_image(color) -> Image.Image:
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = ICON_SIZE // 8
    draw.ellipse((margin, margin, ICON_SIZE - margin, ICON_SIZE - margin), fill=color)
    return image


class TrayApp:
    def __init__(self, args):
        self.args = args
        hotkey = KEY_ALIASES[args.hotkey]
        self.dictation = Dictation(
            args.model,
            hotkey,
            args.language,
            args.paste,
            args.cleanup,
            args.ollama_model,
            on_state_change=self._on_state_change,
        )
        self.icon = pystray.Icon(
            name="wispr-flow-clone",
            icon=make_icon_image(STATE_COLORS["idle"]),
            title="Dictation: idle",
            menu=self._build_menu(),
        )

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(f"Hotkey: {self.args.hotkey}", None, enabled=False),
            pystray.MenuItem(f"Model: {self.args.model}", None, enabled=False),
            pystray.MenuItem(f"Cleanup: {self.args.cleanup}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )

    def _on_state_change(self, state: str):
        self.icon.icon = make_icon_image(STATE_COLORS.get(state, STATE_COLORS["idle"]))
        self.icon.title = f"Dictation: {state}"

    def _quit(self, icon, item):
        icon.stop()

    def run(self):
        listener = keyboard.Listener(
            on_press=self.dictation.on_press, on_release=self.dictation.on_release
        )
        listener.start()
        self.icon.run()  # blocks; must be called on the main thread (required on macOS)


def main():
    args = parse_args()
    TrayApp(args).run()


if __name__ == "__main__":
    main()
