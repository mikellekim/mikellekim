"""Diagnostic: identical to test_tray_full.py except for the icon's name/
title, to test a specific theory - every failed attempt so far reused the
name "wispr-flow-clone" across many abrupt Ctrl+C kills, while the one
script that worked (test_tray_icon.py) used a name that had never been
registered before. Windows can leave a stale/zombie tray icon cache entry
for a name whose owning process was killed without cleanly unregistering
it (Shell_NotifyIcon NIM_DELETE never gets called on Ctrl+C), which can
silently refuse to render future icons under that same identity. If this
script (new name) shows up while test_tray_full.py (old name) doesn't,
that confirms it.
"""

import pystray
from PIL import Image, ImageDraw
from pynput import keyboard

ICON_SIZE = 64
ICON_BACKGROUND = (32, 32, 32)


def make_icon_image(color):
    image = Image.new("RGB", (ICON_SIZE, ICON_SIZE), ICON_BACKGROUND)
    draw = ImageDraw.Draw(image)
    margin = ICON_SIZE // 8
    draw.ellipse((margin, margin, ICON_SIZE - margin, ICON_SIZE - margin), fill=color)
    return image


def fake_checked(item):
    return False


def on_menu_action(icon, item):
    pass


def on_quit(icon, item):
    icon.stop()


def build_menu():
    return pystray.Menu(
        pystray.MenuItem("Hotkey: right_ctrl", None, enabled=False),
        pystray.MenuItem("Model: base", None, enabled=False),
        pystray.MenuItem("Cleanup: rules", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Launch at Login", on_menu_action, checked=fake_checked),
        pystray.MenuItem("Open History Log", on_menu_action, enabled=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )


def on_press(key):
    pass


def on_release(key):
    pass


def main():
    print("Starting keyboard listener...")
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    print("Creating icon with a brand-new name (never used before)...")
    icon = pystray.Icon(
        name="wispr-flow-clone-v2",
        icon=make_icon_image((130, 130, 130)),
        title="Dictation test v2",
        menu=build_menu(),
    )

    def setup(icon):
        icon.visible = True
        print("setup() ran - icon.visible set to True. Check your tray now.")

    icon.run(setup=setup)


if __name__ == "__main__":
    main()
