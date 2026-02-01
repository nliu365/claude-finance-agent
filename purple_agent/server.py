#!/usr/bin/env python3
"""Baseline Purple Agent HTTP server (A2A-compatible schema).

Accepts POST with JSON: {"prompt": "..."}
Returns: {"predictions": [{"id": "...", "factor": "...", "sentiment_score": 0.0, "support_sentences": ["..."]}]}
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List, Dict


def extract_ids_from_prompt(prompt: str) -> List[str]:
    ids = []
    for line in (prompt or "").splitlines():
        line = line.strip()
        if line.lower().startswith("id:"):
            _, value = line.split(":", 1)
            value = value.strip()
            if value:
                ids.append(value)
    return ids


def extract_sentences(prompt: str) -> List[str]:
    sentences = []
    for line in (prompt or "").splitlines():
        line = line.strip()
        if line.lower().startswith("sentence:"):
            _, value = line.split(":", 1)
            value = value.strip()
            if value:
                sentences.append(value)
    return sentences


def build_predictions(prompt: str) -> List[Dict]:
    ids = extract_ids_from_prompt(prompt)
    sentences = extract_sentences(prompt)
    preds = []
    for idx, item_id in enumerate(ids):
        support = sentences[idx] if idx < len(sentences) else ""
        preds.append({
            "id": item_id,
            "factor": "other",
            "sentiment_score": 0.0,
            "support_sentences": [support] if support else [],
        })
    return preds


class PurpleHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: Dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        prompt = payload.get("prompt", "")
        predictions = build_predictions(prompt)
        self._send_json(200, {"predictions": predictions})

    def log_message(self, format, *args):
        return


def main():
    host = os.getenv("PURPLE_HOST", "0.0.0.0")
    port = int(os.getenv("PURPLE_PORT", "8000"))
    server = HTTPServer((host, port), PurpleHandler)
    print(f"Purple Agent baseline server listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
