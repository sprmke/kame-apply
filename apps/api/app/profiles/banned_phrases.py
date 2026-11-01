"""Default banned phrases for voice / answer drafting (human-copy + AI clichés).

Users can edit the list on the voice profile. Apply and Answer Desk lint against it.
"""

from __future__ import annotations

# Seeded once when a voice profile is created. Keep short, lowercase-match friendly.
DEFAULT_BANNED_PHRASES: tuple[str, ...] = (
    # human-copy / marketing fluff
    "seamless",
    "robust",
    "leverage",
    "empower",
    "unlock",
    "elevate",
    "delight",
    "exciting",
    "powerful",
    # AI-default cadence
    "delve",
    "landscape",
    "tapestry",
    "paramount",
    "underscore",
    "pivotal",
    "cutting-edge",
    "game-changer",
    "synergy",
    "utilize",
    "facilitate",
    "in today's world",
    "in conclusion",
    "it is worth noting",
    "as an ai",
    # resume / cover-letter clichés
    "passionate about",
    "results-driven",
    "detail-oriented",
    "team player",
    "think outside the box",
    "hit the ground running",
    "go-getter",
    "self-starter",
    "proven track record",
    "fast-paced environment",
    "dynamic individual",
)
