import logging
import sys

import structlog

# Keys that must never reach logs, whatever the caller passes (pii-guard.mdc).
_REDACTED_KEYS = frozenset(
    {"password", "token", "access_token", "refresh_token", "authorization", "api_key", "secret"}
)


def _scrub(value: object, depth: int = 0) -> object:
    """Recursively redact sensitive keys in nested dicts/lists (depth-limited)."""
    if depth > 6:
        return value
    if isinstance(value, dict):
        return {
            k: ("[redacted]" if str(k).lower() in _REDACTED_KEYS else _scrub(v, depth + 1))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return type(value)(_scrub(v, depth + 1) for v in value)
    return value


def _redact(_logger: object, _method: str, event_dict: structlog.typing.EventDict):
    for key in list(event_dict):
        if key.lower() in _REDACTED_KEYS:
            event_dict[key] = "[redacted]"
        else:
            event_dict[key] = _scrub(event_dict[key])
    return event_dict


def configure_logging(level: str = "INFO", json: bool = True) -> None:
    processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.format_exc_info,
        _redact,
        structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer(),
    ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
