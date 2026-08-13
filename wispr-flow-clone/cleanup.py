"""LLM cleanup pass: strips filler words and false starts, fixes
punctuation and capitalization, and turns spoken punctuation ("period",
"new line") into real punctuation - without changing the wording or
meaning otherwise.

Three backends, all free to use:

- "rules": zero-dependency regex cleanup. Always available, always the
  fallback if a smarter backend is unset or unreachable.
- "ollama": local LLM via a running Ollama server (https://ollama.com) -
  free and private, needs Ollama installed with a model pulled.
- "anthropic": cloud LLM via the Anthropic API - higher quality, costs
  money per call, requires ANTHROPIC_API_KEY.
"""

import json
import re
import urllib.error
import urllib.request
from typing import Optional

CLEANUP_SYSTEM_PROMPT = (
    "You clean up raw speech-to-text transcripts. Fix punctuation, "
    "capitalization, and remove filler words and false starts (um, uh, "
    "like, you know, repeated words). Convert spoken punctuation "
    '("period", "comma", "new line", "question mark") into real '
    "punctuation. Do not change the wording, meaning, or tone, and don't "
    "add or remove any information. Return ONLY the cleaned text, "
    "nothing else."
)

FILLER_PATTERNS = [
    r"\bum+\b", r"\buh+\b", r"\ber+\b", r"\bhmm+\b",
    r"\byou know\b", r"\bi mean\b", r"\bkind of\b", r"\bsort of\b",
    r"\bbasically\b", r"\bliterally\b",
]

SPOKEN_PUNCTUATION = {
    r"\bnew paragraph\b": "\n\n",
    r"\bnew line\b": "\n",
    r"\bexclamation (point|mark)\b": "!",
    r"\bquestion mark\b": "?",
    r"\bperiod\b": ".",
    r"\bcomma\b": ",",
}


def rule_based_cleanup(text: str) -> str:
    """Free, local, zero-dependency cleanup. Always available as a
    fallback when no LLM backend is configured or reachable.
    """
    cleaned = text
    for pattern, replacement in SPOKEN_PUNCTUATION.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    for pattern in FILLER_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\b(\w+)( \1\b)+", r"\1", cleaned, flags=re.IGNORECASE)  # stutters
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" +([,.?!])", r"\1", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    cleaned = cleaned.strip()

    # Sentence-style capitalization/trailing punctuation only makes sense
    # for actual sentences. A single unbroken token (a URL, a domain, a bare
    # word) isn't one - forcing "www.example.com" to "Www.example.com." was
    # a real bug found in testing.
    if cleaned and " " in cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
        if cleaned[-1] not in ".?!":
            cleaned += "."

    return cleaned


def ollama_cleanup(text: str, model: str = "llama3.2:1b", host: str = "http://localhost:11434") -> Optional[str]:
    """Local LLM cleanup via a running Ollama server. Returns None if
    Ollama isn't reachable so the caller can fall back.
    """
    payload = json.dumps(
        {
            "model": model,
            "prompt": f"{CLEANUP_SYSTEM_PROMPT}\n\nTranscript:\n{text}\n\nCleaned:",
            "stream": False,
        }
    ).encode()
    request = urllib.request.Request(
        f"{host}/api/generate", data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read())
        return body.get("response", "").strip() or None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def anthropic_cleanup(
    text: str, api_key: str, model: str = "claude-haiku-4-5-20251001"
) -> Optional[str]:
    """Cloud cleanup via the Anthropic API. Costs money per call. Returns
    None on any failure so the caller can fall back to a free path.
    """
    payload = json.dumps(
        {
            "model": model,
            "max_tokens": 1024,
            "system": CLEANUP_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": text}],
        }
    ).encode()
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read())
        return body["content"][0]["text"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError, OSError):
        return None


def cleanup_text(
    text: str,
    backend: str,
    ollama_model: str = "llama3.2:1b",
    anthropic_api_key: Optional[str] = None,
) -> str:
    """Run the configured cleanup backend. Falls back to the free
    rule-based cleaner if the backend is unreachable or misconfigured.
    "raw" skips cleanup entirely and returns the transcript unchanged.
    """
    if backend == "raw":
        return text

    if backend == "ollama":
        result = ollama_cleanup(text, model=ollama_model)
        if result:
            return result
        print(" [ollama unreachable, falling back to rule-based cleanup]", end="")

    elif backend == "anthropic":
        if anthropic_api_key:
            result = anthropic_cleanup(text, anthropic_api_key)
            if result:
                return result
            print(" [anthropic cleanup failed, falling back to rule-based cleanup]", end="")
        else:
            print(" [ANTHROPIC_API_KEY not set, falling back to rule-based cleanup]", end="")

    return rule_based_cleanup(text)
