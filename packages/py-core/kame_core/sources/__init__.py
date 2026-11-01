"""Job source adapters (Layers 1-3). Network I/O stays in fetch; normalize is pure."""

from kame_core.sources.base import AdapterMeta, RawJob, SourceAdapter, SourceHealth
from kame_core.sources.registry import get_adapter, list_adapters, register_adapter

__all__ = [
    "AdapterMeta",
    "RawJob",
    "SourceAdapter",
    "SourceHealth",
    "get_adapter",
    "list_adapters",
    "register_adapter",
]
