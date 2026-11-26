"""Offline tests for the P0-12 scripts. A local HTTP server stands in for Open Dental. Run: pytest scripts/open_dental/"""

import datetime as dt
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import seed_test_db as seed  # noqa: E402
import smoke_test as smoke  # noqa: E402
from odapi import Client  # noqa: E402

GOOD = "ODFHIR dev-test/cust-test"
PATIENTS = [{"PatNum": 11, "LName": "Fakename", "FName": "Zed", "Birthdate": "1901-01-01", "WirelessPhone": "5035550199"}]
PROVIDERS = [{"ProvNum": n, "Abbr": a} for n, a in enumerate(["DDS1", "HYG1", "HYG2", "DDS2"], 1)]


class Fake(BaseHTTPRequestHandler):
    calls: list[tuple[str, str]] = []
    throttle_after = 10**6
    providers = PROVIDERS

    def _send(self, status: int, body: object = None, headers: dict | None = None) -> None:
        data = json.dumps(body).encode() if body is not None else b""
        self.send_response(status)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle(self) -> None:
        Fake.calls.append((self.command, self.path))
        if self.headers.get("Authorization") != GOOD:
            return self._send(401, {"message": "Invalid customer key"})
        if len(Fake.calls) > Fake.throttle_after:
            return self._send(429, None, {"Retry-After": "1"})
        if self.path.startswith("/patients/Simple"):
            return self._send(200, PATIENTS)
        if self.path == "/providers":
            return self._send(200, Fake.providers)
        if self.path.startswith("/appointments?"):
            return self._send(200, [{"AptNum": 21, "Note": "private"}])
        return self._send(200, [{"Num": 1}, {"Num": 2}])

    do_GET = do_POST = do_PUT = _handle

    def log_message(self, *args: object) -> None:  # keep test output quiet
        pass


@pytest.fixture
def server():
    Fake.calls, Fake.throttle_after, Fake.providers = [], 10**6, PROVIDERS
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def client(base: str) -> Client:
    return Client(base, "dev-test", "cust-test")


def test_smoke_passes_and_prints_no_patient_details(server, capsys):
    c = client(server)
    assert smoke.run(c, "testdb", c.with_customer_key("bad")) == 0
    out = capsys.readouterr().out
    assert "RESULT PASS" in out and "first_patnums=[11]" in out and "aptnums=[21]" in out
    assert "wrong customer key           status=401" in out
    for secret in ("Fakename", "Zed", "1901-01-01", "5035550199", "private", "dev-test", "cust-test"):
        assert secret not in out
    assert all(m == "GET" for m, _ in Fake.calls)  # read-only


def test_smoke_records_429_and_retry_after(server, capsys):
    Fake.throttle_after = 8
    c = client(server)
    assert smoke.run(c, "hosted", c.with_customer_key("bad")) == 0
    out = capsys.readouterr().out
    assert "status=429" in out and "retry_after=['1'" in out


def test_smoke_fails_when_core_get_fails(server, capsys):
    c = Client(server, "dev-test", "wrong")
    assert smoke.run(c, "hosted", c) == 1
    assert "RESULT FAIL" in capsys.readouterr().out


def test_seed_csvs_are_valid():
    assert seed.validate() == []


def test_seed_validation_catches_real_looking_phone(tmp_path):
    for name in ("seed_patients.csv", "seed_appointments.csv"):
        (tmp_path / name).write_text((seed.SEED / name).read_text(encoding="utf-8"), encoding="utf-8")
    p = tmp_path / "seed_patients.csv"
    p.write_text(p.read_text(encoding="utf-8").replace("5035550101", "5034567890"), encoding="utf-8")
    assert any("P01: WirelessPhone" in e for e in seed.validate(tmp_path))


@pytest.mark.parametrize(("target", "key", "why"), [
    ("hosted", "od-customer-key-testdb", "OD_TARGET"),
    ("", "od-customer-key-testdb", "OD_TARGET"),
    ("testdb", "od-customer-key-hosted-test", "--key-name"),
    ("testdb", "od-customer-key-example-dental", "--key-name"),
])
def test_seed_refuses_without_any_request(monkeypatch, server, target, key, why):
    monkeypatch.setenv("OD_TARGET", target)
    assert why in (seed.guard(key, client(server)) or "")
    assert Fake.calls == []


def test_seed_refuses_database_without_our_setup(monkeypatch, server):
    monkeypatch.setenv("OD_TARGET", "testdb")
    Fake.providers = [{"ProvNum": 1, "Abbr": "DOC1"}]  # e.g. the public hosted database
    assert "providers don't match" in seed.guard("od-customer-key-testdb", client(server))
    Fake.providers = PROVIDERS
    assert seed.guard("od-customer-key-testdb", client(server)) is None


def test_main_refuses_hosted_before_reading_keys(monkeypatch, capsys):
    monkeypatch.setenv("OD_TARGET", "hosted")
    monkeypatch.delenv("OD_DEVELOPER_KEY", raising=False)
    assert seed.main(["--key-name", "od-customer-key-testdb"]) == 2
    assert "REFUSED" in capsys.readouterr().err


def test_dates_skip_weekends_holidays_and_late_fridays():
    thu = dt.date(2026, 12, 24)
    assert seed.business_day(thu, 1, dt.time(9), 60) == dt.date(2026, 12, 28)  # 25th holiday, 26-27 weekend
    assert seed.business_day(dt.date(2026, 12, 3), 1, dt.time(14), 60) == dt.date(2026, 12, 7)  # Fri closes 14:00
    assert seed.business_day(dt.date(2026, 12, 3), 1, dt.time(9), 60) == dt.date(2026, 12, 4)
    assert seed.next_dst_monday(dt.date(2026, 11, 26)) == dt.date(2027, 3, 15)


def test_client_repr_hides_keys():
    assert "cust-test" not in repr(client("https://x")) and "dev-test" not in repr(client("https://x"))
