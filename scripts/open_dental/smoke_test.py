"""Read-only smoke test of the Open Dental Remote API (P0-12 spec §10).

  set -a; . ./.env; set +a
  python3 scripts/open_dental/smoke_test.py --target hosted     # Open Dental's public test database
  python3 scripts/open_dental/smoke_test.py --target testdb     # our synthetic test database (B)

Only GET requests (about 22 in total). Prints HTTP statuses, counts, IDs and timings only:
never names, birthdates, phones, addresses or response bodies. Exit 0 if the core GETs return 200.
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from odapi import Client, Result  # noqa: E402

CORE = [  # label, path (D6-D8; list endpoints that work on Open Dental 24.3)
    ("providers", "/providers"),
    ("operatories", "/operatories"),
    ("appointmenttypes", "/appointmenttypes"),
    ("schedules", "/schedules"),
]
LNAME = {"hosted": "smi", "testdb": "Lopez"}  # hosted: Open Dental's own example prefix; testdb: seed P01


def out(label: str, r: Result, extra: str = "") -> None:
    """The only output path: label, status, count, timing. Never the body."""
    count = len(r.data) if isinstance(r.data, list) else (1 if isinstance(r.data, dict) else 0)
    sys.stdout.write(f"{label:<28} status={r.status:<3} count={count:<4} ms={r.ms}{' ' + extra if extra else ''}\n")


def ids(r: Result, key: str, n: int = 5) -> list[int]:
    rows = r.data if isinstance(r.data, list) else []
    return [int(x[key]) for x in rows[:n] if isinstance(x, dict) and str(x.get(key, "")).isdigit()]


def run(client: Client, target: str, wrong: Client) -> int:
    ok = True
    r = client.call("GET", f"/patients/Simple?LName={LNAME[target]}")
    pats = ids(r, "PatNum")
    out("patients/Simple", r, f"first_patnums={pats}")
    ok &= r.status == 200
    for label, path in CORE:
        r = client.call("GET", path)
        out(label, r)
        ok &= r.status == 200
    if pats:
        r = client.call("GET", f"/appointments?PatNum={pats[0]}")
        out("appointments(first patient)", r, f"aptnums={ids(r, 'AptNum')}")
    r = wrong.call("GET", "/operatories")
    out("wrong customer key", r, "(expect 401 or 403)")

    times = []
    start = time.monotonic()
    for _ in range(10):
        r = client.call("GET", "/operatories")
        times.append(r.ms)
        if r.status != 200:
            out("sequential (non-200)", r, f"retry_after={r.retry_after}")
    total = time.monotonic() - start
    times.sort()
    sys.stdout.write(f"{'10 sequential GETs':<28} total_s={total:.1f} rate_per_s={10 / total:.2f} "
                     f"min_ms={times[0]} median_ms={times[5]} max_ms={times[-1]}\n")

    with ThreadPoolExecutor(max_workers=5) as pool:
        par = list(pool.map(lambda _: client.call("GET", "/operatories"), range(5)))
    sys.stdout.write(f"{'5 parallel GETs':<28} statuses={sorted(p.status for p in par)} "
                     f"retry_after={[p.retry_after for p in par if p.retry_after]} "
                     f"max_ms={max(p.ms for p in par)}\n")
    sys.stdout.write("RESULT " + ("PASS" if ok else "FAIL") + "\n")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", choices=["hosted", "testdb"], required=True)
    args = ap.parse_args(argv)
    client = Client.from_env()
    wrong = client.with_customer_key("invalid-customer-key")  # status for a bad key (for P1-15)
    return run(client, args.target, wrong)


if __name__ == "__main__":
    sys.exit(main())
