"""Local-mode terminal prompts for checkpoints (kame-hunt style)."""

from __future__ import annotations

from typing import Any


def prompt_checkpoint(kind: str, detail: dict[str, Any]) -> dict[str, Any]:
    print(f"\n=== Checkpoint: {kind} ===")
    for k, v in (detail or {}).items():
        if k.startswith("_"):
            continue
        print(f"  {k}: {v}")
    if kind == "sensitive_field":
        value = input("Type the value (not stored by the runner beyond one fill): ").rstrip("\n")
        return {"decision": "typed_value", "value": value}
    if kind == "final_review":
        ans = input("[A]pprove submit / [D]eny / [H]andoff / [C]ancel? ").strip().lower()
        if ans.startswith("a"):
            return {"decision": "approve_submit"}
        if ans.startswith("h"):
            return {"decision": "handoff_extension"}
        if ans.startswith("c"):
            return {"decision": "cancel"}
        return {"decision": "deny_submit"}
    if kind in {"login", "captcha"}:
        input("Complete in the browser window, then press Enter to continue…")
        return {"decision": "continue"}
    ans = input("[C]ontinue / [S]kip / [X] cancel? ").strip().lower()
    if ans.startswith("s"):
        return {"decision": "skip"}
    if ans.startswith("x"):
        return {"decision": "cancel"}
    return {"decision": "continue"}
