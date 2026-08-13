"""Diagnostic: reproduces tray_app.py's exact icon/menu structure AND its
concurrent pynput keyboard listener, in the same process - but with no
Dictation/Whisper involved. test_tray_icon.py (bare pystray, no menu, no
listener) showed an icon successfully; tray_app.py (all of it) doesn't.
This sits in between to narrow down which piece is actually responsible.
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
    print("Starting keyboard listener (like tray_app.py's hotkey capture)...")
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    print("Creating icon with tray_app.py's exact menu structure...")
    icon = pystray.Icon(
        name="wispr-flow-clone",
        icon=make_icon_image((130, 130, 130)),
        title="Dictation: idle",
        menu=build_menu(),
    )

    def setup(icon):
        icon.visible = True
        print("setup() ran - icon.visible set to True. Check your tray now.")

    icon.run(setup=setup)


if __name__ == "__main__":
    main()
