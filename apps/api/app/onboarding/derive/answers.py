"""Answer-bank proposals: links, explicit statements, and needs-you rows.

A `resume` answer is approved when the user keeps it. A `default` answer stays unapproved so it
appears in the bank's review list. An eligibility answer is never guessed and never auto-approved.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.onboarding import schemas as s
from app.onboarding.derive import prefs
from app.onboarding.evidence import evidence
from app.profiles.answer_keys import CANONICAL_BY_KEY

_LINK_ANSWERS = (
    ("linkedin_url", "LinkedIn"),
    ("github_url", "GitHub"),
    ("portfolio_url", "Portfolio"),
)
_EEO_KEYS = ("eeo_race", "eeo_gender", "eeo_veteran", "eeo_disability")


def _answer_item(
    *,
    key: str,
    country: str | None,
    answer: str,
    approved: bool,
    source: str,
    reason: str,
    reading_text: str,
    document_id: uuid.UUID,
    quote: str = "",
    confidence: float = 0.9,
    default_on: bool = True,
) -> s.SetupItem:
    target = f"answers.{key}.{country}" if country else f"answers.{key}"
    refs = evidence(document_id, reading_text, quote) if quote else []
    return s.SetupItem(
        id=target,
        group="answers",
        target=target,
        kind="value",
        value={"answer": answer, "approved": approved},
        source=source,  # type: ignore[arg-type]
        confidence=confidence,
        evidence=refs,
        reason_key=reason,
        default_on=default_on,
    )


def _needs_you(target: str, reason: str) -> s.SetupItem:
    return s.SetupItem(
        id=target,
        group="answers",
        target=target,
        kind="value",
        value=None,
        source="you_said",
        confidence=0.0,
        reason_key=reason,
        needs_you=True,
        default_on=True,
    )


def _by_kind(signals: list[prefs.Signal], kind: str) -> prefs.Signal | None:
    return next((signal for signal in signals if signal.kind == kind), None)


def build(
    *,
    text: str,
    document_id: uuid.UUID,
    links: list[dict[str, str]],
    signals: list[prefs.Signal],
    resume_country: str,
) -> list[s.SetupItem]:
    items: list[s.SetupItem] = []

    if links:
        refs = []
        for link in links[:10]:
            refs.extend(evidence(document_id, text, link["url"]))
        if refs:
            items.append(
                s.SetupItem(
                    id="profile.links",
                    group="profile",
                    target="profile.links",
                    kind="list",
                    value=links,
                    source="resume",
                    confidence=0.95,
                    evidence=refs[:10],
                    reason_key="setup.reason.resume_line",
                )
            )
        by_label = {link["label"]: link["url"] for link in reversed(links)}
        for key, label in _LINK_ANSWERS:
            url = by_label.get(label)
            if not url:
                continue
            items.append(
                _answer_item(
                    key=key,
                    country=None,
                    answer=url,
                    approved=True,
                    source="resume",
                    reason="setup.reason.resume_link",
                    reading_text=text,
                    document_id=document_id,
                    quote=url,
                )
            )

    salary_signal = _by_kind(signals, prefs.SignalKind.SALARY)
    if salary_signal is not None and salary_signal.currency:
        try:
            floor = float(str(salary_signal.value).replace(",", "").replace(" ", ""))
        except ValueError:
            floor = None
        if floor:
            refs = evidence(document_id, text, salary_signal.quote)
            if refs:
                items.append(
                    s.SetupItem(
                        id="profile.salary_prefs",
                        group="profile",
                        target="profile.salary_prefs",
                        kind="value",
                        value={
                            "floor": floor,
                            "currency": salary_signal.currency,
                            "period": salary_signal.period or "month",
                        },
                        source="resume",
                        confidence=salary_signal.confidence,
                        evidence=refs,
                        reason_key="setup.reason.stated",
                        default_on=not salary_signal.stale,
                    )
                )

    notice = _by_kind(signals, prefs.SignalKind.NOTICE)
    if notice is not None:
        items.append(
            _answer_item(
                key="notice_period",
                country=None,
                answer=notice.value,
                approved=not notice.stale,
                source="resume",
                reason="setup.reason.stated",
                reading_text=text,
                document_id=document_id,
                quote=notice.quote,
                confidence=notice.confidence,
                default_on=not notice.stale,
            )
        )
    else:
        items.append(_needs_you("answers.notice_period", "setup.reason.needs_you_stated"))

    salary = _by_kind(signals, prefs.SignalKind.SALARY)
    if salary is not None:
        answer = salary.value
        if salary.currency:
            answer = f"{salary.currency} {answer}"
        if salary.period:
            answer = f"{answer} per {salary.period}"
        items.append(
            _answer_item(
                key="salary_expectation",
                country=None,
                answer=answer,
                approved=not salary.stale,
                source="resume",
                reason="setup.reason.stated",
                reading_text=text,
                document_id=document_id,
                quote=salary.quote,
                confidence=salary.confidence,
                default_on=not salary.stale,
            )
        )
    else:
        items.append(
            _answer_item(
                key="salary_expectation",
                country=None,
                answer="Open to discussion",
                approved=False,
                source="default",
                reason="setup.reason.recommended_default",
                reading_text=text,
                document_id=document_id,
                confidence=0.4,
            )
        )

    relocation = _by_kind(signals, prefs.SignalKind.RELOCATION)
    if relocation is not None:
        items.append(
            _answer_item(
                key="relocation",
                country=None,
                answer=relocation.value,
                approved=not relocation.stale,
                source="resume",
                reason="setup.reason.stated",
                reading_text=text,
                document_id=document_id,
                quote=relocation.quote,
                confidence=relocation.confidence,
                default_on=not relocation.stale,
            )
        )
    else:
        items.append(_needs_you("answers.relocation", "setup.reason.needs_you_stated"))

    remote = _by_kind(signals, prefs.SignalKind.REMOTE)
    if remote is not None:
        items.append(
            _answer_item(
                key="remote_preference",
                country=None,
                answer=remote.value,
                approved=not remote.stale,
                source="resume",
                reason="setup.reason.stated",
                reading_text=text,
                document_id=document_id,
                quote=remote.quote,
                confidence=remote.confidence,
                default_on=not remote.stale,
            )
        )

    auth = _by_kind(signals, prefs.SignalKind.WORK_AUTHORIZATION)
    if auth is not None:
        country = (auth.country or resume_country or "").upper() or None
        if country:
            refs = evidence(document_id, text, auth.quote)
            if refs:
                items.append(
                    s.SetupItem(
                        id="profile.work_authorization",
                        group="profile",
                        target="profile.work_authorization",
                        kind="value",
                        value={"countries": [country], "authorized": True},
                        source="resume",
                        confidence=auth.confidence,
                        evidence=refs,
                        reason_key="setup.reason.stated",
                        default_on=not auth.stale,
                    )
                )
            items.append(
                _answer_item(
                    key="work_authorization",
                    country=country,
                    answer=auth.value,
                    approved=not auth.stale,
                    source="resume",
                    reason="setup.reason.stated",
                    reading_text=text,
                    document_id=document_id,
                    quote=auth.quote,
                    confidence=auth.confidence,
                    default_on=not auth.stale,
                )
            )
        else:
            items.append(
                _needs_you("answers.work_authorization", "setup.reason.needs_you_eligibility")
            )
    elif resume_country:
        items.append(
            _needs_you(
                f"answers.work_authorization.{resume_country.upper()}",
                "setup.reason.needs_you_eligibility",
            )
        )
    else:
        items.append(_needs_you("answers.work_authorization", "setup.reason.needs_you_eligibility"))

    sponsorship = _by_kind(signals, prefs.SignalKind.SPONSORSHIP)
    if sponsorship is not None:
        items.append(
            _answer_item(
                key="sponsorship",
                country=None,
                answer=sponsorship.value,
                approved=not sponsorship.stale,
                source="resume",
                reason="setup.reason.stated",
                reading_text=text,
                document_id=document_id,
                quote=sponsorship.quote,
                confidence=sponsorship.confidence,
                default_on=not sponsorship.stale,
            )
        )
    else:
        items.append(_needs_you("answers.sponsorship", "setup.reason.needs_you_eligibility"))

    for key in _EEO_KEYS:
        meta = CANONICAL_BY_KEY[key]
        items.append(
            _answer_item(
                key=key,
                country=None,
                answer=meta.default_answer,
                approved=True,
                source="default",
                reason="setup.reason.recommended_default",
                reading_text=text,
                document_id=document_id,
                confidence=0.5,
            )
        )

    how = CANONICAL_BY_KEY["how_did_you_hear"]
    items.append(
        _answer_item(
            key="how_did_you_hear",
            country=None,
            answer=how.default_answer or "Company career site",
            approved=False,
            source="default",
            reason="setup.reason.recommended_default",
            reading_text=text,
            document_id=document_id,
            confidence=0.4,
        )
    )
    return items


def answer_value(item: s.SetupItem) -> dict[str, Any]:
    """The typed answer payload for one answers item (apply uses this after re-validating)."""
    value = item.value
    return value if isinstance(value, dict) else {"answer": "", "approved": False}
