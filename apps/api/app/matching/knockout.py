"""Predict knockout failures against profile + answer bank."""

from __future__ import annotations

from typing import Any


def predict_knockouts(
    quals: list[dict[str, Any]],
    *,
    profile: dict[str, Any],
    answers: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return knockout hits the candidate likely fails. Empty = pass."""
    hits: list[dict[str, Any]] = []
    auth = profile.get("work_authorization") or {}
    countries = {c.upper() for c in (auth.get("countries") or [])}
    needs_sponsor = bool(auth.get("needs_sponsorship"))
    years = float(profile.get("years_experience") or answers.get("years_experience") or 0)
    degrees = {str(d).lower() for d in (profile.get("degrees") or [])}
    languages = {str(name).lower() for name in (profile.get("languages") or [])}
    licenses = {str(name).lower() for name in (profile.get("licenses") or [])}
    base_country = (answers.get("base_country") or profile.get("country") or "").upper()

    for q in quals:
        if q.get("kind") != "knockout":
            continue
        n = q.get("normalized") or {}
        typ = n.get("type")
        quote = q.get("quote") or q.get("text") or ""
        if typ == "authorization":
            raw = (n.get("raw") or quote).lower()
            if "sponsor" in raw and needs_sponsor:
                hits.append({"qual_id": q.get("id"), "reason": "sponsorship", "quote": quote})
            if any(x in raw for x in ("us citizen", "u.s. citizen", "us based", "based in the us")):
                if "US" not in countries and base_country != "US":
                    hits.append({"qual_id": q.get("id"), "reason": "us_auth", "quote": quote})
        elif typ == "location":
            raw = (n.get("raw") or quote).upper()
            # crude: if quote names a country code the user isn't in
            if base_country and base_country not in raw and "REMOTE" not in raw:
                if any(tok in raw for tok in ("MUST BE BASED", "ONLY CANDIDATES", "ELIGIBLE")):
                    hits.append({"qual_id": q.get("id"), "reason": "location", "quote": quote})
        elif typ == "years":
            need = float(n.get("min_years") or 0)
            if need and years and years + 0.5 < need:
                hits.append(
                    {
                        "qual_id": q.get("id"),
                        "reason": "years",
                        "quote": quote,
                        "need": need,
                        "have": years,
                    }
                )
        elif typ == "degree":
            raw = (n.get("raw") or quote).lower()
            if degrees and not any(d in raw for d in degrees):
                # Only fail when profile has degrees listed and none match wording
                if any(k in raw for k in ("bachelor", "master", "phd", "degree")):
                    hits.append({"qual_id": q.get("id"), "reason": "degree", "quote": quote})
        elif typ == "language":
            name = str(n.get("name") or "").lower()
            if name and name not in languages and languages:
                hits.append({"qual_id": q.get("id"), "reason": "language", "quote": quote})
        elif typ == "license":
            raw = (n.get("raw") or quote).lower()
            if licenses and not any(lic in raw for lic in licenses):
                hits.append({"qual_id": q.get("id"), "reason": "license", "quote": quote})
    return hits
