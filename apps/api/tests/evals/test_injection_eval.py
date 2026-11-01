"""Injection corpus: ≥50 payloads; none may reach AI context clean_text / prompts."""

from __future__ import annotations

import json
from pathlib import Path

from app.safety.sanitize import for_ai_context, sanitize_untrusted_html, sanitize_untrusted_text

FIXTURE = Path(__file__).parent / "fixtures" / "injection" / "payloads.jsonl"

_LEAK_MARKERS = (
    "ignore previous instructions",
    "ignore prior instructions",
    "include the candidate's ssn",
    "include the candidates ssn",
    "system prompt:",
    "ai assistants:",
    "you are an ai",
    "do not tell the user",
)


def test_injection_payloads_never_reach_ai_context():
    rows = [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]
    assert len(rows) >= 50

    for r in rows:
        raw = r["payload"]
        if r.get("html"):
            cleaned = sanitize_untrusted_html(raw).text
        else:
            cleaned = sanitize_untrusted_text(raw).text
        bundle = for_ai_context(raw)
        low = cleaned.lower()
        for marker in _LEAK_MARKERS:
            assert marker not in low, f"marker in clean_text: {marker} :: {r['id']}"
            # Delimited block uses cleaned text only.
            assert marker not in bundle.clean_text.lower(), f"marker in bundle: {r['id']}"
