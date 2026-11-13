"""Local page for the BISAR Calculate action."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from bisar.model import layers_from_screen, loads_from_screen, positions_from_screen
from bisar.report import result_rows
from bisar.solver import analyse

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "web" / "index.html"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = PAGE.read_bytes()
            self._send(200, "text/html; charset=utf-8", body)
            return
        self._send(404, "text/plain; charset=utf-8", b"not found")

    def do_POST(self):
        if self.path != "/api/calculate":
            self._send(404, "text/plain; charset=utf-8", b"not found")
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            layers = layers_from_screen(payload["layers"])
            loads = loads_from_screen(payload["loads"])
            points = positions_from_screen(payload["positions"], layers)
            results = analyse(layers, loads, points)
            body = json.dumps({"results": result_rows(results)}).encode()
            self._send(200, "application/json", body)
        except (KeyError, TypeError, ValueError) as exc:
            message = exc.args[0] if exc.args else str(exc)
            self._send(400, "application/json", json.dumps({"error": str(message)}).encode())

    def log_message(self, fmt, *args):
        print(fmt % args)

    def _send(self, status: int, content_type: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("BISAR calculate is at http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
