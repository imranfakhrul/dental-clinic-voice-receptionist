"""Load the synthetic seed into Open Dental test database (B) (P0-12 spec §6, §7 step 5).

  python3 scripts/open_dental/seed_test_db.py --dry-run
      Check seed_patients.csv and seed_appointments.csv offline. No network.
  set -a; . ./.env; set +a
  python3 scripts/open_dental/seed_test_db.py --key-name od-customer-key-testdb
      Load into test database (B). Refuses unless OD_TARGET=testdb, the key name ends in "-testdb",
      and the database's providers match seed_setup.md (so Open Dental's public hosted database and
      any clinic database are refused).

Prints refs and new PatNum/AptNum only. Paced at 1 request per 1.1 s and honours 429 Retry-After (D3).
"""

import argparse
import csv
import datetime as dt
import os
import re
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
from odapi import Client, Result  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SEED = REPO / "infra/dev/open-dental-test-db/seed"
TZ = ZoneInfo("America/New_York")
PAT_STATUS = {"Patient", "NonPatient", "Inactive", "Archived", "Deceased", "Prospective"}
GENDER = {"Male", "Female", "Unknown"}
APT_STATUS = {"Scheduled", "Broken", "Complete"}
PROVIDERS = {"DDS1", "HYG1", "HYG2"}  # active providers in seed_setup.md
SETUP_ABBRS = {"DDS1", "HYG1", "HYG2", "DDS2"}
TYPES = {"New Patient Exam": 60, "Recall": 60, "Child Recall": 40, "Limited Exam": 30}
PHONE = re.compile(r"55501\d\d$")
HOLIDAYS = {(12, 25), (1, 1)}
FRI_CLOSE = dt.time(14, 0)
PACE_S = 1.1


def load(name: str, seed: Path) -> list[dict[str, str]]:
    with (seed / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def validate(seed: Path = SEED) -> list[str]:
    errs: list[str] = []
    pats, apts = load("seed_patients.csv", seed), load("seed_appointments.csv", seed)
    refs: list[str] = []
    for p in pats:
        r = p["ref"]
        if r in refs:
            errs.append(f"{r}: duplicate ref")
        if not p["LName"] or not p["FName"]:
            errs.append(f"{r}: LName and FName are required")
        if p["Birthdate"]:
            try:
                dt.date.fromisoformat(p["Birthdate"])
            except ValueError:
                errs.append(f"{r}: Birthdate must be yyyy-mm-dd")
        if p["PatStatus"] not in PAT_STATUS or p["Gender"] not in GENDER:
            errs.append(f"{r}: bad PatStatus or Gender")
        for col in ("WirelessPhone", "HmPhone"):
            if p[col] and not PHONE.search(re.sub(r"\D", "", p[col])):
                errs.append(f"{r}: {col} must be a fictional 555-01xx number")
        if p["Email"] and not p["Email"].endswith("@example.com"):
            errs.append(f"{r}: Email must use example.com")
        if p["guarantor_ref"] and p["guarantor_ref"] not in refs:
            errs.append(f"{r}: guarantor {p['guarantor_ref']} must be an earlier row")
        refs.append(r)
    if len(pats) < 30:
        errs.append(f"need at least 30 patients, found {len(pats)}")
    seen: set[str] = set()
    for a in apts:
        r = a["ref"]
        if r in seen:
            errs.append(f"{r}: duplicate ref")
        seen.add(r)
        if a["patient_ref"] not in refs:
            errs.append(f"{r}: unknown patient {a['patient_ref']}")
        if a["prov"] not in PROVIDERS or a["op"] not in {"1", "2", "3", "4"}:
            errs.append(f"{r}: bad provider or operatory")
        if TYPES.get(a["appointment_type"]) != int(a["minutes"]):
            errs.append(f"{r}: {a['appointment_type']} must be {TYPES.get(a['appointment_type'])} minutes")
        if int(a["minutes"]) % 10:
            errs.append(f"{r}: minutes must fit the 10-minute increment")
        if a["status"] not in APT_STATUS:
            errs.append(f"{r}: bad status")
        try:
            when(a, dt.date(2026, 11, 26))
        except ValueError as e:
            errs.append(f"{r}: {e}")
    return errs


def next_dst_monday(today: dt.date) -> dt.date:
    """US DST starts on the second Sunday of March; return the Monday after the next one."""
    for year in (today.year, today.year + 1):
        sundays = [d for d in (dt.date(year, 3, 1) + dt.timedelta(i) for i in range(31)) if d.weekday() == 6]
        if sundays[1] > today:
            return sundays[1] + dt.timedelta(days=1)
    raise ValueError("no DST date found")


def business_day(start: dt.date, n: int, t: dt.time, minutes: int) -> dt.date:
    """Move n open days (negative = back) on which this appointment fits: no weekends or holidays,
    and on Fridays only if it ends by 14:00 (decision log B5)."""
    end = (dt.datetime.combine(start, t) + dt.timedelta(minutes=minutes)).time()

    def fits(x: dt.date) -> bool:
        return (x.month, x.day) not in HOLIDAYS and (x.weekday() < 4 or (x.weekday() == 4 and end <= FRI_CLOSE))

    d, step = start, (1 if n >= 0 else -1)
    for _ in range(abs(n)):
        d += dt.timedelta(days=step)
        while not fits(d):
            d += dt.timedelta(days=step)
    while not fits(d):
        d += dt.timedelta(days=step)
    return d


def when(a: dict[str, str], today: dt.date) -> dt.datetime:
    t = dt.time.fromisoformat(a["time"])
    m = re.fullmatch(r"([+-]\d+) business days", a["day"])
    if m:
        d = business_day(today, int(m.group(1)), t, int(a["minutes"]))
    elif a["day"].startswith("first Monday after the next US DST change"):
        d = next_dst_monday(today)
    else:
        raise ValueError(f"can't read day {a['day']!r}")
    return dt.datetime.combine(d, t, TZ)


class Paced:
    def __init__(self, client: Client) -> None:
        self.client, self.last = client, 0.0

    def call(self, method: str, path: str, body: dict | None = None) -> Result:
        for _ in range(5):
            time.sleep(max(0.0, self.last + PACE_S - time.monotonic()))
            r = self.client.call(method, path, body)
            self.last = time.monotonic()
            if r.status != 429:
                return r
            time.sleep(float(r.retry_after or 5))
        return r


def guard(key_name: str, client: Client | None) -> str | None:
    """Why loading must be refused, or None. The first two checks send no request."""
    if os.environ.get("OD_TARGET", "").strip() != "testdb":
        return "OD_TARGET must be 'testdb' (never the public hosted database or a clinic)"
    if not key_name.endswith("-testdb"):
        return "--key-name must end in '-testdb'"
    if client is None:
        return None
    r = client.call("GET", "/providers")
    abbrs = {p.get("Abbr") for p in r.data} if r.status == 200 and isinstance(r.data, list) else set()
    if abbrs != SETUP_ABBRS:
        return "providers don't match seed_setup.md; this is not test database (B) after setup"
    return None


def seed(client: Client, today: dt.date) -> int:
    api = Paced(client)
    types = api.call("GET", "/appointmenttypes")
    provs = api.call("GET", "/providers")
    type_num = {t["AppointmentTypeName"]: t["AppointmentTypeNum"] for t in (types.data or [])}
    prov_num = {p["Abbr"]: p["ProvNum"] for p in (provs.data or [])}
    patnum: dict[str, int] = {}
    for p in load("seed_patients.csv", SEED):
        body = {k: p[k] for k in ("LName", "FName", "MiddleI", "Preferred", "Gender", "Birthdate", "PatStatus",
                                  "WirelessPhone", "HmPhone", "Email") if p[k]}
        if p["guarantor_ref"]:
            body["Guarantor"] = patnum[p["guarantor_ref"]]
        r = api.call("POST", "/patients", body)
        num = r.data.get("PatNum") if isinstance(r.data, dict) else None
        sys.stdout.write(f"{p['ref']} status={r.status} PatNum={num}\n")
        if num:
            patnum[p["ref"]] = int(num)
    for a in load("seed_appointments.csv", SEED):
        if a["patient_ref"] not in patnum:
            sys.stdout.write(f"{a['ref']} skipped: patient {a['patient_ref']} not created\n")
            continue
        hyg = a["prov"].startswith("HYG")
        body = {"PatNum": patnum[a["patient_ref"]], "Op": int(a["op"]),
                "AptDateTime": when(a, today).strftime("%Y-%m-%d %H:%M:%S"),
                "Pattern": "X" * (int(a["minutes"]) // 5),
                "AppointmentTypeNum": type_num.get(a["appointment_type"], 0),
                "ProvNum": prov_num["DDS1"], "IsHygiene": "true" if hyg else "false",
                "AptStatus": "Complete" if a["status"] == "Complete" else "Scheduled"}
        if hyg:
            body["ProvHyg"] = prov_num[a["prov"]]
        r = api.call("POST", "/appointments", body)
        num = r.data.get("AptNum") if isinstance(r.data, dict) else None
        sys.stdout.write(f"{a['ref']} status={r.status} AptNum={num}\n")
        if num and a["status"] == "Broken":
            b = api.call("PUT", f"/appointments/{num}/Break", {"sendToUnscheduledList": "true"})
            sys.stdout.write(f"{a['ref']} break status={b.status}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--key-name", default="")
    args = ap.parse_args(argv)
    errs = validate()
    for e in errs:
        sys.stderr.write(f"ERROR {e}\n")
    if errs:
        return 1
    today = dt.datetime.now(TZ).date()
    if args.dry_run:
        pats, apts = load("seed_patients.csv", SEED), load("seed_appointments.csv", SEED)
        sys.stdout.write(f"OK {len(pats)} patients, {len(apts)} appointments\n")
        for a in apts:
            sys.stdout.write(f"  {a['ref']} {when(a, today):%Y-%m-%d %a %H:%M %Z}\n")
        return 0
    why = guard(args.key_name, None)
    if why:
        sys.stderr.write(f"REFUSED {why}\n")
        return 2
    client = Client.from_env()
    why = guard(args.key_name, client)
    if why:
        sys.stderr.write(f"REFUSED {why}\n")
        return 2
    return seed(client, today)


if __name__ == "__main__":
    sys.exit(main())
