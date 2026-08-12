# wispr-flow-clone

A free, local push-to-talk dictation tool: hold a hotkey, speak, release it,
and the transcription is typed into whatever window has focus.

Runs entirely on your machine via [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
(a fast Whisper build). No cloud API, no per-minute cost, no audio sent
anywhere after the one-time model download.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Run

```bash
python flow.py
```

Hold **F9**, speak, release it - the text is typed into the focused app.

Or run it as a menu-bar/tray app instead of a terminal script:

```bash
python tray_app.py
```

This runs the exact same engine in the background with a tray icon that
shows status at a glance (gray = idle, red = recording, orange =
transcribing) plus a menu with the active settings and a Quit item. It
takes the same flags as `flow.py` (`--hotkey`, `--model`, `--cleanup`, etc).

Options:

```bash
python flow.py --hotkey right_ctrl --model small --language en
python flow.py --paste   # paste via clipboard instead of simulated typing
python flow.py --cleanup ollama --ollama-model llama3.2:1b
python flow.py --cleanup anthropic   # needs ANTHROPIC_API_KEY set
```

- `--model`: `tiny` / `base` / `small` / `medium` / `large-v3`. Bigger models
  are more accurate and slower. `base` is a good default on CPU.
- `--language`: skip language auto-detection if you always dictate in one
  language (slightly faster and more reliable).
- `--paste`: uses your clipboard + Cmd/Ctrl+V instead of typing each
  character - faster for long text but temporarily overwrites your
  clipboard.

## Cleanup pass

Whisper's raw output keeps every "um", stutter, and spoken-out punctuation
("period", "new line"). `--cleanup` runs a pass to fix that before the text
is typed:

- `rules` (default) - free, local, zero setup. A regex pass that strips
  filler words (um, uh, you know, kind of, ...), collapses stutters,
  converts spoken punctuation to real punctuation, and fixes capitalization.
  Always available, and the automatic fallback for the other two backends.
- `ollama` - routes the transcript through a local LLM via a running
  [Ollama](https://ollama.com) server for smarter cleanup (better at
  judgment calls like restructuring a rambling sentence). Free and private,
  but needs Ollama installed and a model pulled, e.g. `ollama pull
  llama3.2:1b`. Falls back to `rules` if the server isn't reachable.
- `anthropic` - routes the transcript through the Anthropic API for the
  highest-quality cleanup. Requires `ANTHROPIC_API_KEY` and costs a small
  amount per call. Falls back to `rules` if the key is missing or the call
  fails.
- `raw` - skip cleanup entirely, type exactly what Whisper produced.

## Launch at login

`tray_app.py` can register itself to start automatically when you log in,
so it behaves like a real background app instead of something you have to
remember to launch:

```bash
python tray_app.py --enable-autostart              # registers with current flags
python tray_app.py --model small --enable-autostart # e.g. with the small model
python tray_app.py --disable-autostart
python tray_app.py --autostart-status
```

Whatever flags you pass alongside `--enable-autostart` (hotkey, model,
cleanup backend, ...) are what gets re-run at login. You can also toggle it
from the tray icon's "Launch at Login" menu item at any time, which reuses
the flags the running instance was started with.

Implementation is native per OS - no extra background service:

- **macOS**: a LaunchAgent plist at `~/Library/LaunchAgents/com.wispr-flow-clone.plist`.
- **Windows**: a value under `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`.
- **Linux**: an XDG autostart file at `~/.config/autostart/wispr-flow-clone.desktop`.

## Platform notes

- **macOS**: grant your terminal (or the packaged app, if you build one)
  Accessibility and Microphone permissions in System Settings > Privacy &
  Security, or the hotkey/typing won't work.
- **Windows**: should work out of the box; run from an elevated terminal if
  the hotkey doesn't register in some apps.
- **Linux**: works under X11. Wayland restricts global key listening and
  synthetic typing for security reasons, so `pynput` may not work there
  without extra setup (e.g. running under XWayland or using `ydotool`). The
  tray icon (`tray_app.py`) additionally needs a system tray/AppIndicator
  implementation - e.g. `sudo apt install gir1.2-appindicator3-0.1` on
  Ubuntu/GNOME - or it won't render.

## How it works

1. `pynput` listens globally for the hotkey (default `F9`).
2. While held, `sounddevice` records mono 16kHz audio from your default mic.
3. On release, the audio buffer is fed straight to a local `faster-whisper`
   model (no ffmpeg/file round-trip needed).
4. The raw transcript is run through the configured `--cleanup` backend
   (see above) to strip filler words and fix punctuation.
5. The cleaned text is typed into the focused window via `pynput`, or
   pasted via the clipboard with `--paste`.

`tray_app.py` wraps the same `Dictation` class from `flow.py` with a
`pystray` icon: the hotkey listener runs on a background thread while
`pystray`'s event loop runs on the main thread (required on macOS), and a
state-change callback repaints the icon on idle/recording/transcribing.

## Ideas for next steps

- Persist a dictation history.
- Add a small settings UI instead of flag-only configuration.
- Auto-select model size based on detected CPU/GPU.
- Add a toggle mode (tap to start/stop) in addition to push-to-talk.
