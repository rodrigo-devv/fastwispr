from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import platform
import secrets
import tempfile
from typing import Any

from .config import Config, load_config
from .db import Store
from .pipeline import process_text_with_store


class DevRunnerState:
    def __init__(self, config: Config, token: str | None):
        self.config = config
        self.token = token


def load_or_create_token(path: str | Path | None) -> str | None:
    if path is None:
        return None
    token_path = Path(path).expanduser()
    if token_path.exists():
        return token_path.read_text(encoding="utf-8").strip()
    token = secrets.token_hex(32)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(token + "\n", encoding="utf-8")
    return token


def make_handler(state: DevRunnerState):
    class DevRunnerHandler(BaseHTTPRequestHandler):
        server_version = "FastWisprDevRunner/0.1"

        def log_message(self, format: str, *args: object) -> None:
            print(f"{self.address_string()} - {format % args}")

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            if not state.token:
                return True
            return self.headers.get("X-FastWispr-Dev-Token") == state.token

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length == 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("JSON body must be an object")
            return data

        def _require_auth(self) -> bool:
            if self._authorized():
                return True
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "invalid token"})
            return False

        def do_GET(self) -> None:
            if not self._require_auth():
                return
            try:
                if self.path == "/health":
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "ok": True,
                            "pid": os.getpid(),
                            "platform": platform.platform(),
                            "python": platform.python_version(),
                            "db_path": str(state.config.db_path),
                        },
                    )
                    return
                if self.path == "/audio/devices":
                    self._audio_devices()
                    return
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "unknown endpoint"})
            except Exception as exc:  # pragma: no cover - safety response path
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})

        def do_POST(self) -> None:
            if not self._require_auth():
                return
            try:
                body = self._read_json()
                if self.path == "/process":
                    self._process(body)
                    return
                if self.path == "/record-smoke":
                    self._record_smoke(body)
                    return
                if self.path == "/paste":
                    self._paste(body)
                    return
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "unknown endpoint"})
            except Exception as exc:  # pragma: no cover - safety response path
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})

        def _audio_devices(self) -> None:
            try:
                sd = __import__("sounddevice")
            except ImportError as exc:
                self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"ok": False, "error": str(exc)})
                return
            devices = sd.query_devices()
            self._send_json(HTTPStatus.OK, {"ok": True, "devices": str(devices)})

        def _process(self, body: dict[str, Any]) -> None:
            text = str(body.get("text", ""))
            with Store(state.config.db_path) as store:
                processed = process_text_with_store(text, store)
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "raw": processed.raw,
                    "final": processed.final,
                    "snippet_expanded": processed.snippet_expanded,
                },
            )

        def _record_smoke(self, body: dict[str, Any]) -> None:
            seconds = float(body.get("seconds", 1.0))
            seconds = max(0.1, min(seconds, 5.0))
            from .windows.audio import SounddeviceRecorder

            with tempfile.TemporaryDirectory(prefix="fastwispr-record-smoke-") as tmp:
                output = Path(tmp) / "smoke.wav"
                path = SounddeviceRecorder().record_seconds(output, seconds)
                size = path.stat().st_size
            self._send_json(HTTPStatus.OK, {"ok": True, "seconds": seconds, "bytes_recorded": size})

        def _paste(self, body: dict[str, Any]) -> None:
            text = str(body.get("text", ""))
            if not text:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "text is required"})
                return
            from .windows.injector import ClipboardPasteInjector

            ClipboardPasteInjector(restore_clipboard=state.config.restore_clipboard).paste_text(text)
            self._send_json(HTTPStatus.OK, {"ok": True, "chars": len(text)})

    return DevRunnerHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fastwispr-dev-runner")
    parser.add_argument("--config", help="Path to config.toml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token-file", help="Path to a local token file")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    token = load_or_create_token(args.token_file)
    state = DevRunnerState(config, token)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    print(f"FastWispr dev runner listening on http://{args.host}:{args.port}")
    if token:
        print("Token auth enabled via X-FastWispr-Dev-Token")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
