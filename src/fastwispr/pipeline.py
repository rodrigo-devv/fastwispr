from __future__ import annotations

from dataclasses import dataclass

from .db import DictionaryEntry, Snippet, Store
from .polish import apply_corrections, apply_dictionary, expand_snippet, finish_sentence, remove_fillers


@dataclass(frozen=True)
class ProcessedText:
    raw: str
    final: str
    snippet_expanded: bool = False


def process_text(
    raw: str,
    *,
    dictionary: list[DictionaryEntry] | None = None,
    snippets: list[Snippet] | None = None,
) -> ProcessedText:
    cleaned = remove_fillers(apply_corrections(raw))
    snippet = expand_snippet(cleaned, snippets or [])
    if snippet is not None:
        return ProcessedText(raw=raw, final=snippet, snippet_expanded=True)
    final = finish_sentence(apply_dictionary(cleaned, dictionary or []))
    return ProcessedText(raw=raw, final=final)


def process_text_with_store(raw: str, store: Store, app_name: str | None = None) -> ProcessedText:
    return process_text(raw, dictionary=store.dictionary_entries(), snippets=store.snippets(app_name))
