"""Dedupe precision: same title at the same company is not enough to merge requisitions."""

from app.core.ssrf import is_public_http_url_literal
from app.jobs.dedupe import same_job


def _same(**over: object) -> bool:
    base: dict[str, object] = dict(
        company_a="Acme",
        title_a="Software Engineer",
        simhash_a=1234,
        company_b="Acme",
        title_b="Software Engineer",
        simhash_b=1234,
        locations_a=[{"city": "Austin", "country": "US"}],
        locations_b=[{"city": "Austin", "country": "US"}],
    )
    base.update(over)
    return same_job(**base)  # type: ignore[arg-type]


def test_identical_posting_merges():
    assert _same() is True


def test_same_company_and_title_in_different_cities_does_not_merge():
    assert (
        _same(
            locations_a=[{"city": "Austin", "country": "US"}],
            locations_b=[{"city": "Berlin", "country": "DE"}],
        )
        is False
    )


def test_unknown_location_on_one_side_still_merges():
    assert _same(locations_a=[], locations_b=[{"city": "Berlin"}]) is True


def test_remote_vs_onsite_city_does_not_merge():
    assert _same(locations_a=["Remote"], locations_b=["New York, NY"]) is False


def test_different_title_does_not_merge():
    assert _same(title_b="Senior Software Engineer") is False


def test_different_company_does_not_merge():
    assert _same(company_b="Globex") is False


def test_stored_urls_must_be_public_http():
    assert is_public_http_url_literal("https://boards.greenhouse.io/acme/jobs/1")
    assert not is_public_http_url_literal("http://169.254.169.254/latest/meta-data")
    assert not is_public_http_url_literal("http://127.0.0.1:8100/api/v1/healthz")
    assert not is_public_http_url_literal("http://localhost/admin")
    assert not is_public_http_url_literal("file:///etc/passwd")
    assert not is_public_http_url_literal("http://10.0.0.5/internal")
