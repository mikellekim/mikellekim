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

Options:

```bash
python flow.py --hotkey right_ctrl --model small --language en
python flow.py --paste   # paste via clipboard instead of simulated typing
```

- `--model`: `tiny` / `base` / `small` / `medium` / `large-v3`. Bigger models
  are more accurate and slower. `base` is a good default on CPU.
- `--language`: skip language auto-detection if you always dictate in one
  language (slightly faster and more reliable).
- `--paste`: uses your clipboard + Cmd/Ctrl+V instead of typing each
  character - faster for long text but temporarily overwrites your
  clipboard.

## Platform notes

- **macOS**: grant your terminal (or the packaged app, if you build one)
  Accessibility and Microphone permissions in System Settings > Privacy &
  Security, or the hotkey/typing won't work.
- **Windows**: should work out of the box; run from an elevated terminal if
  the hotkey doesn't register in some apps.
- **Linux**: works under X11. Wayland restricts global key listening and
  synthetic typing for security reasons, so `pynput` may not work there
  without extra setup (e.g. running under XWayland or using `ydotool`).

## How it works

1. `pynput` listens globally for the hotkey (default `F9`).
2. While held, `sounddevice` records mono 16kHz audio from your default mic.
3. On release, the audio buffer is fed straight to a local `faster-whisper`
   model (no ffmpeg/file round-trip needed).
4. The resulting text is typed into the focused window via `pynput`, or
   pasted via the clipboard with `--paste`.

## Ideas for next steps

- Package as a menu-bar/tray app (e.g. with `rumps` on macOS, `pystray`
  cross-platform) instead of a terminal script.
- Add an LLM cleanup pass (filler-word removal, punctuation, formatting)
  using a local model or an API key you provide.
- Persist a dictation history.
- Auto-select model size based on detected CPU/GPU.
- Add a toggle mode (tap to start/stop) in addition to push-to-talk.
