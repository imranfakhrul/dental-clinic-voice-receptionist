"""Tiny Open Dental Remote API helper shared by the P0-12 scripts. Standard library only.

Keys come from the environment (OD_DEVELOPER_KEY, OD_CUSTOMER_KEY, OPEN_DENTAL_BASE_URL) and are never printed.
This is a throwaway tool for P0-12; the real client with throttling and retries is P1-15.
"""

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE = "https://api.opendental.com/api/v1"
TIMEOUT_S = 70  # Open Dental returns 504 after 60 s (D3)


@dataclass
class Result:
    status: int
    data: Any
    ms: int
    retry_after: str | None = None


class Client:
    def __init__(self, base: str, developer_key: str, customer_key: str) -> None:
        self.base = base.rstrip("/")
        self._dev = developer_key
        self._auth = f"ODFHIR {developer_key}/{customer_key}"

    def with_customer_key(self, customer_key: str) -> "Client":
        return Client(self.base, self._dev, customer_key)

    @classmethod
    def from_env(cls, customer_key: str | None = None) -> "Client":
        dev = os.environ.get("OD_DEVELOPER_KEY", "").strip()
        cust = (customer_key if customer_key is not None else os.environ.get("OD_CUSTOMER_KEY", "")).strip()
        if not dev or not cust:
            raise SystemExit("OD_DEVELOPER_KEY and OD_CUSTOMER_KEY must be set (see .env.example)")
        return cls(os.environ.get("OPEN_DENTAL_BASE_URL", DEFAULT_BASE).strip() or DEFAULT_BASE, dev, cust)

    def __repr__(self) -> str:  # never show the keys
        return f"Client(base={self.base!r})"

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Result:
        req = urllib.request.Request(
            self.base + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": self._auth, "Content-Type": "application/json",
                     "User-Agent": "dai-rcpt-p0-12/0.1"},
        )
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310 (fixed https base)
                raw = resp.read()
                status, retry = resp.status, resp.headers.get("Retry-After")
        except urllib.error.HTTPError as e:
            raw, status, retry = b"", e.code, e.headers.get("Retry-After") if e.headers else None
        except (urllib.error.URLError, TimeoutError):
            raw, status, retry = b"", 0, None
        ms = int((time.monotonic() - start) * 1000)
        try:
            data = json.loads(raw) if raw else None
        except ValueError:
            data = None
        return Result(status, data, ms, retry)
