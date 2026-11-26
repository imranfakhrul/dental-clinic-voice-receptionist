"""Send one WhatsApp test template message through the Meta Cloud API (P0-07 test only).

Synthetic content only, to a team phone only. Never use it with patient data.
P4-01 builds the real adapter.

Three modes:
  (default)  the `hello_world` template; works any time.
  --template <id>
             one of our templates from docs/messaging/templates.yaml (P0-15), only when its provider_status is
             APPROVED, filled with that template's own example values (fictional). No other values can be given.
  --text     a fixed plain-text TEST message (TEST_TEXT below). WhatsApp allows free text only
             inside the 24-hour window, so first send any message (e.g. "hi") from your phone
             to the test number, then run this within 24 hours.

Environment (set in your shell from your password manager; never commit them):
  WA_TOKEN              access token (temporary test token or system-user token)
  WA_PHONE_NUMBER_ID    the test business phone number ID
  WA_TEST_TO            the team phone that receives it, digits with country code
  WA_GRAPH_VERSION      optional, default v27.0

Output: the HTTP status and the message ID only. The token and phone number are never printed.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

TIMEOUT_SECONDS = 15
TEST_TEXT = (
    "TEST ONLY - Dental AI receptionist (P0-07 WhatsApp test). "
    "This is not a real appointment and contains no patient information. Please ignore."
)


def _redact(text: str) -> str:
    """Hide anything that looks like a phone number or a long token."""
    text = re.sub(r"\+?\d[\d\s-]{6,}\d", "<number>", text)
    return re.sub(r"[A-Za-z0-9_-]{40,}", "<token>", text)


TEMPLATES = Path(__file__).resolve().parents[2] / "docs/messaging/templates.yaml"


def template_message(template_id: str, path: Path | None = None) -> dict[str, object]:
    """WhatsApp template payload for an APPROVED template, with its example values only."""
    import yaml  # only needed in --template mode

    data = yaml.safe_load((path or TEMPLATES).read_text(encoding="utf-8"))
    found = [t for t in data["templates"] if t["id"] == template_id]
    if not found or found[0]["channel"] != "whatsapp":
        raise ValueError("unknown WhatsApp template id")
    t = found[0]
    if t.get("provider_status") != "APPROVED":
        raise ValueError(f"template is {t.get('provider_status')}, not APPROVED")
    names = list(dict.fromkeys(re.findall(r"\{([a-z_]+)\}", t["body"])))
    params = [{"type": "text", "parameter_name": n, "text": t["example"][n]} for n in names]
    return {"type": "template", "template": {
        "name": t["provider_template_name"], "language": {"code": t["language"]},
        "components": [{"type": "body", "parameters": params}],
    }}


def _open(request: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 - fixed https URL


def main(argv: list[str] | None = None, opener: Callable[..., Any] = _open) -> int:
    args = sys.argv[1:] if argv is None else argv
    # Pasted values often carry spaces, line breaks, quotes, "+" or "-": clean them first.
    token = "".join(os.environ.get("WA_TOKEN", "").split()).strip("'\"")
    phone_number_id = re.sub(r"\D", "", os.environ.get("WA_PHONE_NUMBER_ID", ""))
    to = re.sub(r"\D", "", os.environ.get("WA_TEST_TO", ""))
    version = os.environ.get("WA_GRAPH_VERSION", "v27.0").strip()
    problems = []
    if not token:
        problems.append("WA_TOKEN is empty")
    if not phone_number_id:
        problems.append("WA_PHONE_NUMBER_ID is empty or has no digits")
    if len(to) < 8:
        problems.append("WA_TEST_TO must be your number with country code, digits only (e.g. 8801XXXXXXXXX)")
    if not re.fullmatch(r"v\d+\.\d+", version):
        problems.append("WA_GRAPH_VERSION must look like v27.0")
    if problems:
        sys.stderr.write("Check your environment variables:\n" + "".join(f"  - {p}\n" for p in problems))
        return 2
    url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"
    body: dict[str, object] = {"messaging_product": "whatsapp", "to": to}
    if args == ["--text"]:
        body |= {"type": "text", "text": {"body": TEST_TEXT}}
    elif not args:
        body |= {"type": "template", "template": {"name": "hello_world", "language": {"code": "en_US"}}}
    elif len(args) == 2 and args[0] == "--template":
        try:
            body |= template_message(args[1])
        except (ValueError, KeyError, OSError) as err:
            sys.stderr.write(f"Refused: {err}\n")
            return 2
    else:
        sys.stderr.write("Usage: send_test_message.py [--text | --template <id>]\n")
        return 2
    request = urllib.request.Request(  # noqa: S310 - fixed https URL
        url,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener(request, TIMEOUT_SECONDS) as response:
            data = json.load(response)
            ids = [m.get("id", "?") for m in data.get("messages", [])]
            sys.stdout.write(f"HTTP {response.status}: accepted, message id(s): {', '.join(ids)}\n")
            sys.stdout.write("Accepted is not delivered: watch the webhook probe for 'sent' and 'delivered'.\n")
            return 0
    except urllib.error.HTTPError as err:
        try:
            error = json.load(err).get("error", {})
            detail = f"code {error.get('code')}: {_redact(str(error.get('message', '')))}"
        except (ValueError, AttributeError):
            detail = "no error body"
        sys.stderr.write(f"HTTP {err.code}: {detail}\n")
        if "--text" in args:
            sys.stderr.write("For --text, first send any message from your phone to the test number (24-hour window).\n")
        return 1
    except urllib.error.URLError as err:
        sys.stderr.write(f"Network error: {type(err.reason).__name__}\n")
        return 1
    except (ValueError, OSError) as err:
        sys.stderr.write(f"Request could not be sent: {type(err).__name__}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
