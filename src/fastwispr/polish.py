from __future__ import annotations

import re
from typing import Iterable

from .db import DictionaryEntry, Snippet

FILLERS = ("um", "uh", "erm", "hmm", "you know")
CORRECTION_MARKERS = ("actually", "no wait", "i mean", "sorry")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def remove_fillers(text: str) -> str:
    cleaned = text
    for filler in FILLERS:
        cleaned = re.sub(rf"(?i)(?<!\w){re.escape(filler)}(?!\w)[,\s]*", "", cleaned)
    return normalize_whitespace(cleaned)


def apply_corrections(text: str) -> str:
    cleaned = normalize_whitespace(text)
    cleaned = re.sub(r"(?is)^.*\bscratch that\b\s*", "", cleaned)
    for marker in CORRECTION_MARKERS:
        pattern = rf"(?i)\b(\w+)\s+{re.escape(marker)}\s+(\w+)\b"
        previous = None
        while previous != cleaned:
            previous = cleaned
            cleaned = re.sub(pattern, r"\2", cleaned)
    return normalize_whitespace(cleaned)


def expand_snippet(text: str, snippets: Iterable[Snippet]) -> str | None:
    normalized = normalize_for_match(text)
    for snippet in snippets:
        if normalize_for_match(snippet.cue) == normalized:
            return snippet.body
    return None


def apply_dictionary(text: str, entries: Iterable[DictionaryEntry]) -> str:
    cleaned = text
    for entry in entries:
        if not entry.term:
            continue
        cleaned = re.sub(rf"(?i)(?<!\w){re.escape(entry.term)}(?!\w)", entry.replacement, cleaned)
    return cleaned


def finish_sentence(text: str) -> str:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return ""
    cleaned = cleaned[0].upper() + cleaned[1:]
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def normalize_for_match(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
