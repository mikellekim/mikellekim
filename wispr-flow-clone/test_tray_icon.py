"""Minimal standalone pystray test, unrelated to the rest of this project.

Diagnostic only: run this directly (python test_tray_icon.py) to check
whether pystray can show ANY icon in your system tray at all. If this also
fails to appear, the problem is pystray/Windows on this machine in general,
not something specific to tray_app.py - which tells us where to look next.
"""

import pystray
from PIL import Image, ImageDraw


def make_image():
    image = Image.new("RGB", (64, 64), "red")
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill="blue")
    return image


def on_quit(icon, item):
    icon.stop()


def setup(icon):
    icon.visible = True
    print("setup() ran - icon.visible set to True")


def main():
    print("Creating icon...")
    icon = pystray.Icon(
        "test_tray_icon",
        make_image(),
        "Test Icon - right-click to quit",
        menu=pystray.Menu(pystray.MenuItem("Quit", on_quit)),
    )
    print("Calling icon.run() - a red circle on blue background should appear in your tray now.")
    icon.run(setup=setup)
    print("icon.run() returned - icon closed.")


if __name__ == "__main__":
    main()
