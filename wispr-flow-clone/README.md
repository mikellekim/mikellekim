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

### Desktop shortcut (Windows)

To avoid retyping the command every time, `start_tray.bat` launches the
tray app with a fixed set of flags. Edit the `python tray_app.py ...` line
inside it to change hotkey/model/cleanup, then make a one-click desktop
launcher:

1. Right-click `start_tray.bat` in File Explorer.
2. **Send to** > **Desktop (create shortcut)**.
3. Double-click the new desktop icon whenever you want to start it - no
   Command Prompt typing needed.

It still opens a console window so you can see the transcript/cleanup log
like before; the window closes on its own only if you close it (a `pause`
at the end keeps it open if something errors, so you can read why).

By default the shortcut gets a generic `.bat` file icon. To give it a
proper custom icon (`assets/app_icon.ico`, a mic glyph):

1. Right-click the desktop shortcut > **Properties**.
2. On the **Shortcut** tab, click **Change Icon...**.
3. If Windows warns the file has no icons, click **OK** to browse anyway.
4. Click **Browse...**, navigate to `wispr-flow-clone\assets\app_icon.ico`,
   select it, then **OK** > **OK**.

The desktop icon updates immediately.

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

## History log

Every transcription (both the raw Whisper output and the cleaned-up text)
is appended to a local log at `~/.wispr-flow-clone/history.jsonl` - one
JSON object per line, timestamped, nothing sent anywhere.

Browse it with `history.py`:

```bash
python history.py                # last 20 entries
python history.py --limit 100
python history.py --search budget
python history.py --clear        # delete the log
```

From the tray app, "Open History Log" opens the file directly in your
default text editor. Disable logging entirely with `--no-history`, or
point it elsewhere with `--history-path /some/path.jsonl`:

```bash
python flow.py --no-history
python tray_app.py --history-path ~/Documents/dictation.jsonl
```

## Whisper hallucinations

On quiet or ambiguous audio, Whisper occasionally locks onto the wrong
language and loops the same word or phrase (e.g. `"gydwchwb, gydwchwb,
gydwchwb, gydwchwb"`) instead of transcribing silence or noise - a known
failure mode of the underlying model, not specific to this project. When a
transcript is dominated by one repeated word, it's treated as a likely
hallucination and discarded (not typed, not logged) rather than dumped into
whatever you were typing into. If you hit this often, try `--language en`
(skips language auto-detection, the usual trigger) or a larger `--model`.

## Platform notes

- **macOS**: grant your terminal (or the packaged app, if you build one)
  Accessibility and Microphone permissions in System Settings > Privacy &
  Security, or the hotkey/typing won't work.
- **Windows**: should work out of the box. If the real Wispr Flow app (or
  any other tool with its own global hotkey) is running, it can compete
  for the same hotkey and cause flaky, hard-to-explain behavior - quit it
  before testing. Typing won't reach a window running elevated ("Run as
  Administrator") unless this script is also run elevated - that's
  Windows' own UIPI security boundary blocking lower-privilege processes
  from injecting input into higher-privilege windows, not a bug here.
  If the tray icon ever stops appearing after repeatedly force-killing
  `tray_app.py` (Ctrl+C, closing the console window, Task Manager) instead
  of quitting it via its own "Quit" menu item: Windows can leave a stale
  cached entry for that icon's identity that silently blocks it from
  rendering again, even though nothing errors. Always prefer the tray
  menu's Quit over force-killing the process, since that cleanly
  unregisters the icon.
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
5. Both the raw and cleaned text are appended to the history log (see
   above), unless `--no-history` is set.
6. The cleaned text is typed into the focused window via `pynput`, or
   pasted via the clipboard with `--paste`.

`tray_app.py` wraps the same `Dictation` class from `flow.py` with a
`pystray` icon: the hotkey listener runs on a background thread while
`pystray`'s event loop runs on the main thread (required on macOS), and a
state-change callback repaints the icon on idle/recording/transcribing.

## Ideas for next steps

- Add a small settings UI instead of flag-only configuration.
- Auto-select model size based on detected CPU/GPU.
- Add a toggle mode (tap to start/stop) in addition to push-to-talk.
