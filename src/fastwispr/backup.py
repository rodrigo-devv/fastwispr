from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from .config_edit import merge_config_dict, read_config_dict
from .db import Store

BACKUP_VERSION = 1


def export_payload(config_path: Path, store: Store) -> dict[str, Any]:
    return {
        "version": BACKUP_VERSION,
        "config": read_config_dict(config_path),
        "dictionary": [
            {"term": entry.term, "replacement": entry.replacement}
            for entry in store.dictionary_entries()
        ],
        "snippets": [
            {"cue": snippet.cue, "body": snippet.body, "app_scope": snippet.app_scope}
            for snippet in store.snippets()
        ],
    }


def write_backup(config_path: Path, store: Store, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(export_payload(config_path, store), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_backup(input_path: Path) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    validate_backup_payload(payload)
    return payload


def import_backup(config_path: Path, store: Store, input_path: Path) -> dict[str, int]:
    payload = read_backup(input_path)
    config = payload.get("config", {})
    if config:
        merge_config_dict(config_path, config)
    dictionary_count = 0
    for item in payload.get("dictionary", []):
        store.upsert_dictionary(str(item["term"]), str(item["replacement"]))
        dictionary_count += 1
    snippet_count = 0
    for item in payload.get("snippets", []):
        store.upsert_snippet(str(item["cue"]), str(item["body"]), item.get("app_scope"))
        snippet_count += 1
    return {"dictionary": dictionary_count, "snippets": snippet_count}


def validate_backup_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Backup payload must be a JSON object")
    if payload.get("version") != BACKUP_VERSION:
        raise ValueError(f"Unsupported backup version: {payload.get('version')!r}")
    for key in ("dictionary", "snippets"):
        value = payload.get(key, [])
        if not isinstance(value, list):
            raise ValueError(f"Backup field {key!r} must be a list")
    config = payload.get("config", {})
    if not isinstance(config, dict):
        raise ValueError("Backup field 'config' must be an object")
