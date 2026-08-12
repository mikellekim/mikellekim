#!/usr/bin/env python3
"""
Free, local push-to-talk dictation, in the spirit of Wispr Flow.

Hold a hotkey, speak, release it, and the transcribed text is typed into
whatever window has focus. Transcription runs locally via faster-whisper
(a CTranslate2 build of Whisper) - no cloud API, no per-minute cost, no
audio leaving your machine (after the one-time model download).
"""

import argparse
import os
import platform
import sys
import threading
from typing import List, Optional

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput import keyboard

from cleanup import cleanup_text

SAMPLE_RATE = 16000
MIN_DURATION_SECONDS = 0.3

KEY_ALIASES = {
    "f8": keyboard.Key.f8,
    "f9": keyboard.Key.f9,
    "right_ctrl": keyboard.Key.ctrl_r,
    "right_alt": keyboard.Key.alt_r,
    "pause": keyboard.Key.pause,
}


class Dictation:
    def __init__(
        self,
        model_size: str,
        hotkey: keyboard.Key,
        language: Optional[str],
        paste_mode: bool,
        cleanup_backend: str,
        ollama_model: str,
    ):
        print(f"Loading Whisper model '{model_size}' (first run downloads it)...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.hotkey = hotkey
        self.language = language
        self.paste_mode = paste_mode
        self.cleanup_backend = cleanup_backend
        self.ollama_model = ollama_model
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.controller = keyboard.Controller()

        self._recording = False
        self._frames: List[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()

        print("Ready. Hold the hotkey to record, release to transcribe and type.")

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        with self._lock:
            self._frames.append(indata.copy())

    def start_recording(self):
        with self._lock:
            if self._recording:
                return
            self._recording = True
            self._frames = []
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=self._audio_callback
        )
        self._stream.start()
        print("\n[recording]", end="", flush=True)

    def stop_recording_and_transcribe(self):
        with self._lock:
            if not self._recording:
                return
            self._recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            frames, self._frames = self._frames, []

        if not frames:
            print(" (nothing captured)")
            return

        audio = np.concatenate(frames, axis=0).flatten()
        duration = len(audio) / SAMPLE_RATE
        if duration < MIN_DURATION_SECONDS:
            print(" (too short, ignored)")
            return

        print(f" transcribing {duration:.1f}s...", end="", flush=True)
        segments, _ = self.model.transcribe(audio, language=self.language, beam_size=5)
        raw_text = "".join(segment.text for segment in segments).strip()
        if not raw_text:
            print(" (empty)")
            return
        print(f" -> {raw_text!r}", end="")

        text = cleanup_text(
            raw_text,
            self.cleanup_backend,
            ollama_model=self.ollama_model,
            anthropic_api_key=self.anthropic_api_key,
        )
        print(f" | cleaned -> {text!r}" if text != raw_text else "")

        if text:
            self._emit(text)

    def _emit(self, text: str):
        if self.paste_mode:
            import pyperclip

            pyperclip.copy(text)
            modifier = keyboard.Key.cmd if platform.system() == "Darwin" else keyboard.Key.ctrl
            with self.controller.pressed(modifier):
                self.controller.press("v")
                self.controller.release("v")
        else:
            self.controller.type(text + " ")

    def on_press(self, key):
        if key == self.hotkey:
            self.start_recording()

    def on_release(self, key):
        if key == self.hotkey:
            self.stop_recording_and_transcribe()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hotkey", default="f9", choices=sorted(KEY_ALIASES), help="push-to-talk key (default: f9)"
    )
    parser.add_argument(
        "--model",
        default="base",
        help="faster-whisper model size: tiny/base/small/medium/large-v3 (default: base)",
    )
    parser.add_argument(
        "--language", default=None, help="force a language code (e.g. en); default: auto-detect"
    )
    parser.add_argument(
        "--paste",
        action="store_true",
        help="paste via clipboard (Cmd/Ctrl+V) instead of typing character-by-character",
    )
    parser.add_argument(
        "--cleanup",
        default="rules",
        choices=["raw", "rules", "ollama", "anthropic"],
        help=(
            "cleanup pass for filler words and punctuation (default: rules - free, local, "
            "no setup). 'ollama' uses a local LLM via a running Ollama server; 'anthropic' "
            "uses the Anthropic API (needs ANTHROPIC_API_KEY, costs money per call); 'raw' "
            "skips cleanup entirely. Both LLM backends fall back to 'rules' if unreachable."
        ),
    )
    parser.add_argument(
        "--ollama-model",
        default="llama3.2:1b",
        help="model to use with --cleanup ollama (default: llama3.2:1b)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    hotkey = KEY_ALIASES[args.hotkey]
    dictation = Dictation(
        args.model, hotkey, args.language, args.paste, args.cleanup, args.ollama_model
    )

    with keyboard.Listener(on_press=dictation.on_press, on_release=dictation.on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
