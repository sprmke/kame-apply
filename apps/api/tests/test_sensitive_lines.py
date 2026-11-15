"""Sensitive-class line removal: PH, MY, IN, DE, AE CV headers plus an ordinary resume."""

from __future__ import annotations

import pytest

from app.onboarding.sensitive_lines import strip_sensitive_lines

PH_CV = """ANA REYES
Makati City, Philippines
Petsa ng Kapanganakan: 12 May 1990
Edad: 34
Kasarian: Babae
Katayuang Sibil: Single
Nasyonalidad: Filipino
Relihiyon: Roman Catholic
SSS No: 12-3456789-0
TIN: 123-456-789
PhilHealth: 12-345678901-2
Skills: onboarding, Zendesk
"""

MY_CV = """Ahmad bin Ali
Kuala Lumpur, Malaysia
Tarikh Lahir: 1 Januari 1992
Umur: 32
Jantina: Lelaki
Status Perkahwinan: Berkahwin
Warganegara: Malaysia
Agama: Islam
No. NRIC: 920101-14-5678
Pengalaman: 5 tahun dalam logistik
"""

IN_CV = """Priya Sharma
Bengaluru, India
Date of Birth: 03/04/1991
Age: 33
Gender: Female
Marital Status: Married
Nationality: Indian
Religion: Hindu
Aadhaar: 1234 5678 9012
PAN No: ABCDE1234F
Skills: Python, SQL
"""

DE_CV = """Lena Müller
Berlin, Deutschland
Geburtsdatum: 14.02.1988
Geschlecht: weiblich
Familienstand: verheiratet
Staatsangehörigkeit: deutsch
Geburtsort: Hamburg
Konfession: keine
Ausweisnummer: 1234567890
Berufserfahrung
2019 - 2025 Produktmanagerin bei Acme
"""

AE_CV = """Omar Haddad
Dubai, United Arab Emirates
Date of Birth: 20 June 1987
Nationality: Lebanese
Marital Status: Married
Religion: Islam
Passport No: A12345678
Emirates ID: 784-1987-1234567-1
Visa Status: Employment visa
Skills: logistics, procurement
"""

ORDINARY = """Ana Reyes
Customer Support Lead
Manila, Philippines
ana.reyes@example.com

Skills: onboarding, Zendesk, SQL
Experience
2020 - 2025 Support Lead at Acme
Age of the team: 12 people
Heightened security awareness training for support staff
"""


@pytest.mark.parametrize(
    "cv",
    [PH_CV, MY_CV, IN_CV, DE_CV, AE_CV],
    ids=["ph", "my", "in", "de", "ae"],
)
def test_sensitive_header_lines_are_removed(cv):
    result = strip_sensitive_lines(cv)
    lowered = result.text.casefold()
    for marker in (
        "1990",
        "1991",
        "1987",
        "1988",
        "1234 5678 9012",
        "abcde1234f",
        "920101",
        "784-1987",
        "a12345678",
        "1234567890",
    ):
        assert marker.casefold() not in lowered
    assert result.removed >= 4
    assert result.kinds


def test_removed_text_keeps_the_facts_setup_needs():
    result = strip_sensitive_lines(PH_CV)
    assert "Makati City, Philippines" in result.text
    assert "Skills: onboarding, Zendesk" in result.text


def test_ordinary_resume_lines_are_kept():
    result = strip_sensitive_lines(ORDINARY)
    assert result.removed == 0
    assert "Support Lead at Acme" in result.text
    assert "Heightened security awareness training" in result.text
    assert "Age of the team" in result.text


def test_reference_section_is_removed_to_the_end():
    text = """Ana Reyes
Skills: SQL
References
Maria Santos, +63 917 000 0000
Jose Cruz, jose@example.com
"""
    result = strip_sensitive_lines(text)
    assert "Maria Santos" not in result.text
    assert "jose@example.com" not in result.text
    assert "references" in result.kinds
    assert "Skills: SQL" in result.text


def test_filter_is_idempotent():
    once = strip_sensitive_lines(PH_CV)
    twice = strip_sensitive_lines(once.text)
    assert twice.text == once.text
    assert twice.removed == 0
