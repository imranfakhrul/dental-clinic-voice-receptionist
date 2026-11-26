"""Local receiver for Meta WhatsApp webhooks, to prove the signature scheme (P0-07 test only).

- GET  /  answers Meta's verification request (hub.mode, hub.verify_token, hub.challenge).
- POST /  checks X-Hub-Signature-256 (HMAC-SHA256 of the raw body with the app secret) and
          prints PASS or FAIL plus event types and status values. Message text, phone numbers
          and IDs are never printed, and nothing is saved.

Environment (from your password manager; never commit them):
  WA_APP_SECRET     the app secret (App settings > Basic)
  WA_VERIFY_TOKEN   any random string you also type into the webhook settings
Usage:
  python3 scripts/messaging/webhook_probe.py [port]      # default port 8080
  python3 scripts/messaging/webhook_probe.py --self-test # local check, no network
P4-06 builds the real endpoint.
"""

import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY_BYTES = 1_000_000


def signature_ok(body: bytes, header: str | None, app_secret: str) -> bool:
    """True if header is 'sha256=<hex HMAC-SHA256 of body keyed with app_secret>'."""
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def summarise(body: bytes) -> list[str]:
    """Event types and status values only: no text, numbers or IDs."""
    try:
        payload = json.loads(body)
    except ValueError:
        return ["body is not JSON"]
    lines = [f"object={payload.get('object')}"]
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            lines.append(f"field={change.get('field')}")
            for status in value.get("statuses", []):
                errors = [e.get("code") for e in status.get("errors", [])]
                lines.append(f"  status={status.get('status')}" + (f" error_codes={errors}" if errors else ""))
            for message in value.get("messages", []):
                lines.append(f"  inbound message type={message.get('type')} (content not shown)")
    return lines


def make_handler(app_secret: str, verify_token: str, out=sys.stdout) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            pass  # the default log line would print the query string, which holds the verify token

        def _reply(self, code: int, text: str = "") -> None:
            data = text.encode()
            self.send_response(code)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            mode = query.get("hub.mode", [""])[0]
            token = query.get("hub.verify_token", [""])[0]
            challenge = query.get("hub.challenge", [""])[0]
            if mode == "subscribe" and hmac.compare_digest(token, verify_token):
                out.write("GET verification: PASS (challenge returned)\n")
                self._reply(200, challenge)
            else:
                out.write("GET verification: FAIL (wrong mode or token)\n")
                self._reply(403)
            out.flush()

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            if length > MAX_BODY_BYTES:
                self._reply(413)
                return
            body = self.rfile.read(length)
            if not signature_ok(body, self.headers.get("X-Hub-Signature-256"), app_secret):
                out.write("POST signature: FAIL\n")
                self._reply(401)
            else:
                out.write("POST signature: PASS\n" + "\n".join(summarise(body)) + "\n")
                self._reply(200)
            out.flush()

    return Handler


def self_test() -> int:
    """Run the receiver on a local port and send it signed and wrongly signed requests."""
    secret, token = secrets.token_hex(16), secrets.token_hex(8)
    log: list[str] = []

    class Sink:
        def write(self, s: str) -> None:
            log.append(s)

        def flush(self) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(secret, token, Sink()))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/"
    body = json.dumps({"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages",
           "value": {"statuses": [{"id": "synthetic", "status": "delivered", "recipient_id": "0000000"}]}}]}]}).encode()

    def post(key: str) -> int:
        sig = "sha256=" + hmac.new(key.encode(), body, hashlib.sha256).hexdigest()
        req = urllib.request.Request(base, data=body, headers={"X-Hub-Signature-256": sig}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:  # noqa: S310 - local test server
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    def get(tok: str) -> int:
        q = urllib.parse.urlencode({"hub.mode": "subscribe", "hub.verify_token": tok, "hub.challenge": "1234"})
        try:
            with urllib.request.urlopen(base + "?" + q, timeout=5) as r:  # noqa: S310 - local test server
                return r.status if r.read() == b"1234" else -1
        except urllib.error.HTTPError as e:
            return e.code

    results = {
        "right secret -> 200": post(secret) == 200,
        "wrong secret -> 401": post("wrong-secret") == 401,
        "right verify token -> 200 + challenge": get(token) == 200,
        "wrong verify token -> 403": get("wrong") == 403,
        "nothing secret or numeric ID printed": not any(secret in s or token in s or "0000000" in s for s in log),
    }
    server.shutdown()
    sys.stdout.write("".join(log))
    for name, ok in results.items():
        sys.stdout.write(f"{'PASS' if ok else 'FAIL'}  {name}\n")
    return 0 if all(results.values()) else 1


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        return self_test()
    app_secret, verify_token = os.environ.get("WA_APP_SECRET"), os.environ.get("WA_VERIFY_TOKEN")
    if not app_secret or not verify_token:
        sys.stderr.write("Set WA_APP_SECRET and WA_VERIFY_TOKEN first.\n")
        return 2
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app_secret, verify_token))
    sys.stdout.write(f"Listening on http://127.0.0.1:{port}/  (Ctrl+C to stop)\n")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
