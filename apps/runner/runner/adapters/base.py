from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass(frozen=True)
class Adapter:
    key: str
    host_needles: tuple[str, ...]
    # normalized label substring → canonical key
    field_map: dict[str, str] = field(default_factory=dict)
    next_selectors: tuple[str, ...] = (
        "button:has-text('Next')",
        "button:has-text('Continue')",
        "button:has-text('Save and Continue')",
        # Never a bare input[type=submit]: on single-page forms that is the Submit control.
        "input[type=submit][value*='next' i]",
        "input[type=submit][value*='continue' i]",
    )
    submit_selectors: tuple[str, ...] = (
        "button:has-text('Submit')",
        "button:has-text('Submit application')",
        "input[value='Submit']",
        "input[value*='submit' i]",
    )
    confirmation_needles: tuple[str, ...] = (
        "application submitted",
        "application received",
        "we received your application",
        "successfully applied",
        "thank you for applying",
        "your application has been received",
    )
    login_needles: tuple[str, ...] = (
        "sign in to continue",
        "log in to continue",
        "sign in to apply",
        "create an account to apply",
    )


_ADAPTERS: list[Adapter] = [
    Adapter(
        key="greenhouse",
        host_needles=("boards.greenhouse.io", "greenhouse.io"),
        field_map={
            "first name": "first_name",
            "last name": "last_name",
            "email": "email",
            "phone": "phone",
            "resume": "resume",
            "cover letter": "summary",
            "linkedin": "linkedin_url",
        },
    ),
    Adapter(
        key="lever",
        host_needles=("jobs.lever.co", "lever.co"),
        field_map={
            "full name": "full_name",
            "email": "email",
            "phone": "phone",
            "resume": "resume",
            "linkedin": "linkedin_url",
        },
    ),
    Adapter(
        key="ashby",
        host_needles=("jobs.ashbyhq.com", "ashbyhq.com"),
        field_map={
            "first name": "first_name",
            "last name": "last_name",
            "email": "email",
            "phone": "phone",
            "resume": "resume",
        },
    ),
    Adapter(
        key="workable",
        host_needles=("apply.workable.com", "workable.com"),
        field_map={"first name": "first_name", "last name": "last_name", "email": "email"},
    ),
    Adapter(
        key="smartrecruiters",
        host_needles=("smartrecruiters.com",),
        field_map={"first name": "first_name", "last name": "last_name", "email": "email"},
    ),
    Adapter(
        key="workday",
        host_needles=("myworkdayjobs.com", "workday.com"),
        field_map={
            "email address": "email",
            "password": "password",
            "first name": "first_name",
            "last name": "last_name",
        },
        login_needles=("create account", "sign in", "password"),
    ),
    Adapter(
        key="icims",
        host_needles=("icims.com",),
        field_map={"email": "email", "first name": "first_name", "last name": "last_name"},
    ),
    Adapter(
        key="successfactors",
        host_needles=("successfactors", "sap.com"),
        field_map={"email": "email"},
    ),
    Adapter(key="generic", host_needles=()),
]


def detect_adapter(url: str) -> Adapter:
    host = (urlparse(url).hostname or "").lower()
    path = (urlparse(url).path or "").lower()
    blob = f"{host}{path}"
    for a in _ADAPTERS:
        if a.key == "generic":
            continue
        if any(n in blob for n in a.host_needles):
            return a
    return _ADAPTERS[-1]


def get_adapter(key: str) -> Adapter:
    for a in _ADAPTERS:
        if a.key == key:
            return a
    return _ADAPTERS[-1]
