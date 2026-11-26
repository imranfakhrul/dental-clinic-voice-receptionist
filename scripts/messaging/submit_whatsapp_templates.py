"""Submit the WhatsApp templates in docs/messaging/templates.yaml to Meta for review (P0-15).

  python3 scripts/messaging/submit_whatsapp_templates.py            # dry run (default): no network call
  python3 scripts/messaging/submit_whatsapp_templates.py --submit   # creates the templates on the WhatsApp Business Account

Run --submit only when the user says so. Synthetic example values only (the templates' own examples).
Before submitting, run check_templates.py: this script refuses if it reports errors.

Environment (from your shell or the git-ignored .env; never commit them):
  WA_TOKEN          access token with whatsapp_business_management permission
  WA_WABA_ID        WhatsApp Business Account ID
  WA_GRAPH_VERSION  optional, default v27.0

API (source M11): POST https://graph.facebook.com/<version>/<WABA_ID>/message_templates with name, language,
category "utility", parameter_format "named" and a body component with example.body_text_named_params.
Output: template name, Meta template ID and status only. The token, account ID and bodies are never printed.
After a successful submit, set provider_status: SUBMITTED in templates.yaml and update the registration record.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import check_templates  # noqa: E402

TIMEOUT_SECONDS = 15
VAR = re.compile(r"\{([a-z_]+)\}")


def to_named(body: str) -> str:
    """{first_name} -> {{first_name}} (Meta named parameter format)."""
    return VAR.sub(lambda m: "{{" + m.group(1) + "}}", body)


def payload(template: dict[str, Any]) -> dict[str, Any]:
    names = list(dict.fromkeys(VAR.findall(template["body"])))  # order of first use, no duplicates
    return {
        "name": template["provider_template_name"],
        "language": template["language"],
        "category": "utility",
        "parameter_format": "named",
        "components": [{
            "type": "body",
            "text": to_named(template["body"]),
            "example": {"body_text_named_params": [
                {"param_name": n, "example": template["example"][n]} for n in names
            ]},
        }],
    }


def whatsapp_templates(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [t for t in data["templates"] if t["channel"] == "whatsapp"]


def _redact(text: str) -> str:
    text = re.sub(r"\+?\d[\d\s-]{6,}\d", "<number>", text)
    return re.sub(r"[A-Za-z0-9_-]{40,}", "<token>", text)


Opener = Callable[[urllib.request.Request, float], Any]


def _open(request: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 - fixed https URL


def main(argv: list[str] | None = None, opener: Opener = _open, env: dict[str, str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--submit", action="store_true", help="really create the templates (default: dry run)")
    ap.add_argument("--templates", type=Path, default=check_templates.TEMPLATES)
    a = ap.parse_args(argv)
    env = dict(os.environ) if env is None else env

    data = yaml.safe_load(a.templates.read_text(encoding="utf-8"))
    policy = yaml.safe_load(check_templates.POLICY.read_text(encoding="utf-8"))
    schema = json.loads(check_templates.SCHEMA.read_text(encoding="utf-8"))
    if any(f.level == "error" for f in check_templates.check(data, policy, schema)):
        sys.stderr.write("check_templates.py reports errors: fix them first (nothing submitted).\n")
        return 2
    todo = [t for t in whatsapp_templates(data) if t["provider_status"] in ("DRAFT", "REJECTED")]

    token = "".join(env.get("WA_TOKEN", "").split()).strip("'\"")
    waba = re.sub(r"\D", "", env.get("WA_WABA_ID", ""))
    version = env.get("WA_GRAPH_VERSION", "v27.0").strip()
    if not a.submit or not token or not waba:
        why = "dry run" if not a.submit else "dry run: WA_TOKEN or WA_WABA_ID is empty"
        sys.stdout.write(f"{why}; {len(todo)} template(s) would be submitted:\n")
        for t in todo:
            p = payload(t)
            params = [x["param_name"] for x in p["components"][0]["example"]["body_text_named_params"]]
            sys.stdout.write(f"  {p['name']} ({p['language']}, utility) params: {', '.join(params)}\n")
        return 0 if not a.submit else 2
    if not re.fullmatch(r"v\d+\.\d+", version):
        sys.stderr.write("WA_GRAPH_VERSION must look like v27.0\n")
        return 2

    url = f"https://graph.facebook.com/{version}/{waba}/message_templates"
    failed = 0
    for t in todo:
        request = urllib.request.Request(  # noqa: S310 - fixed https URL
            url, data=json.dumps(payload(t)).encode(), method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        name = t["provider_template_name"]
        try:
            with opener(request, TIMEOUT_SECONDS) as response:
                result = json.load(response)
                sys.stdout.write(f"{name}: id {result.get('id', '?')} status {result.get('status', '?')}\n")
        except urllib.error.HTTPError as err:
            failed += 1
            try:
                error = json.load(err).get("error", {})
                detail = f"code {error.get('code')}: {_redact(str(error.get('message', '')))}"
            except (ValueError, AttributeError):
                detail = "no error body"
            sys.stderr.write(f"{name}: HTTP {err.code} {detail}\n")
        except (urllib.error.URLError, OSError, ValueError) as err:
            failed += 1
            sys.stderr.write(f"{name}: request failed ({type(err).__name__})\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
