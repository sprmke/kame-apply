"""Cap MCP tool payloads so Claude Code does not truncate blindly."""

from __future__ import annotations

import json
from typing import Any

# ~8k tokens ≈ 32k chars rough budget for default tool results.
DEFAULT_MAX_CHARS = 32_000
JOB_TEXT_MAX_CHARS = 48_000


def trim_payload(data: Any, *, max_chars: int = DEFAULT_MAX_CHARS) -> Any:
    raw = json.dumps(data, default=str)
    if len(raw) <= max_chars:
        return data
    if isinstance(data, dict):
        out = dict(data)
        out["_truncated"] = True
        out["_note"] = f"Result truncated to ~{max_chars} chars; fetch details by id."
        # Prefer keeping ids/summaries
        for key in ("description", "description_text", "source_text", "content", "html"):
            if key in out and isinstance(out[key], str) and len(out[key]) > 2000:
                out[key] = out[key][:2000] + "…"
        raw2 = json.dumps(out, default=str)
        if len(raw2) <= max_chars:
            return out
        return {
            "truncated": True,
            "summary_keys": list(data.keys()) if isinstance(data, dict) else [],
            "hint": "Use a more specific tool or pagination.",
        }
    if isinstance(data, list):
        kept: list[Any] = []
        for item in data:
            kept.append(item)
            if len(json.dumps(kept, default=str)) > max_chars:
                kept.pop()
                break
        return {"items": kept, "truncated": True, "returned": len(kept), "total_hint": len(data)}
    return {"truncated": True, "preview": str(data)[: max_chars - 50]}
