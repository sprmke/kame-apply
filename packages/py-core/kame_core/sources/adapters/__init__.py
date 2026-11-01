"""Import side-effect: register built-in adapters."""

from kame_core.sources.adapters import ats_ashby as ats_ashby
from kame_core.sources.adapters import ats_greenhouse as ats_greenhouse
from kame_core.sources.adapters import ats_lever as ats_lever
from kame_core.sources.adapters import ats_recruitee as ats_recruitee
from kame_core.sources.adapters import ats_smartrecruiters as ats_smartrecruiters
from kame_core.sources.adapters import ats_workable as ats_workable
from kame_core.sources.adapters import board_arbeitnow as board_arbeitnow
from kame_core.sources.adapters import board_himalayas as board_himalayas
from kame_core.sources.adapters import board_jobicy as board_jobicy
from kame_core.sources.adapters import board_muse as board_muse
from kame_core.sources.adapters import board_remoteok as board_remoteok
from kame_core.sources.adapters import board_remotive as board_remotive
from kame_core.sources.adapters import career_jsonld as career_jsonld

__all__ = [
    "ats_ashby",
    "ats_greenhouse",
    "ats_lever",
    "ats_recruitee",
    "ats_smartrecruiters",
    "ats_workable",
    "board_arbeitnow",
    "board_himalayas",
    "board_jobicy",
    "board_muse",
    "board_remoteok",
    "board_remotive",
    "career_jsonld",
]
