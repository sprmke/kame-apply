"""L1 content rules loaded from rules.yaml."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

RULES_PATH = Path(__file__).with_name("rules.yaml")


@dataclass(frozen=True)
class RuleHit:
    rule_id: str
    signal: str
    weight: int
    evidence: str
    layer: str = "L1"


@lru_cache(maxsize=1)
def load_rules() -> dict[str, Any]:
    return yaml.safe_load(RULES_PATH.read_text()) or {}


def content_rule_hits(text: str) -> list[RuleHit]:
    cfg = load_rules()
    hits: list[RuleHit] = []
    blob = text or ""
    for rule in cfg.get("rules") or []:
        pat = rule.get("pattern") or ""
        if not pat:
            continue
        m = re.search(pat, blob)
        if not m:
            continue
        quote = m.group(0).strip()
        if len(quote) > 160:
            quote = quote[:157] + "..."
        hits.append(
            RuleHit(
                rule_id=str(rule.get("id") or "rule"),
                signal=str(rule.get("signal") or rule.get("id") or "content"),
                weight=int(rule.get("weight") or 10),
                evidence=quote,
            )
        )
    return hits


def thresholds() -> dict[str, Any]:
    return dict(load_rules().get("thresholds") or {})


def ats_host_patterns() -> list[str]:
    return list(load_rules().get("ats_hosts") or [])
