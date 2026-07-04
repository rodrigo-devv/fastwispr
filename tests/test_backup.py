from pathlib import Path
import json

from fastwispr.cli import main
from fastwispr.db import Store


def write_config(config_path: Path, db_path: Path) -> None:
    config_path.write_text(f'[storage]\ndb_path = "{db_path.as_posix()}"\n[stt]\nlanguage = "en"\n', encoding="utf-8")


def test_backup_export_writes_versioned_json_without_history(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "fastwispr.sqlite3"
    export_path = tmp_path / "backup.json"
    write_config(config_path, db_path)
    with Store(db_path) as store:
        store.upsert_dictionary("tail scale", "Tailscale")
        store.upsert_snippet("insert scheduling link", "https://cal.com/rodrigo")
        store.record_dictation_event(raw_transcript="secret audio words", final_text="secret", latency_ms=1)

    assert main(["--config", str(config_path), "backup", "export", str(export_path)]) == 0

    payload = json.loads(export_path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["dictionary"] == [{"term": "tail scale", "replacement": "Tailscale"}]
    assert payload["snippets"] == [{"cue": "insert scheduling link", "body": "https://cal.com/rodrigo", "app_scope": None}]
    assert payload["config"]["stt"]["language"] == "en"
    assert "history" not in payload
    assert "dictation_events" not in payload
    assert "secret audio words" not in export_path.read_text(encoding="utf-8")


def test_backup_import_appends_dictionary_snippets_and_config(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "fastwispr.sqlite3"
    import_path = tmp_path / "backup.json"
    write_config(config_path, db_path)
    import_path.write_text(
        json.dumps(
            {
                "version": 1,
                "config": {"stt": {"language": "pt-BR"}, "injection": {"restore_clipboard": False}},
                "dictionary": [{"term": "rog flow", "replacement": "ROG Flow"}],
                "snippets": [{"cue": "insert email", "body": "devv.rodrigo@gmail.com", "app_scope": None}],
            }
        ),
        encoding="utf-8",
    )

    assert main(["--config", str(config_path), "backup", "import", str(import_path)]) == 0

    with Store(db_path) as store:
        assert store.dictionary_entries()[0].replacement == "ROG Flow"
        assert store.snippets()[0].body == "devv.rodrigo@gmail.com"
    config_text = config_path.read_text(encoding="utf-8")
    assert 'language = "pt-BR"' in config_text
    assert "restore_clipboard = false" in config_text
