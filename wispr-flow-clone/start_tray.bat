@echo off
REM Double-click launcher for the tray app (or make a desktop shortcut to
REM this file - see README.md "Desktop shortcut" section). Runs from
REM wherever this .bat file lives, so it works regardless of your current
REM directory. Edit the flags on the line below to change hotkey/model/etc.
cd /d "%~dp0"
python tray_app.py --language en --hotkey right_ctrl
pause
