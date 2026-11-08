"""Page loop for one apply run. Never clicks Submit unless submit_approved is true."""

from __future__ import annotations

import base64
import logging
import tempfile
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, Page

from runner.adapters.base import detect_adapter
from runner.agent_fallback import constrained_fill
from runner.blur import screenshot_blurred
from runner.client import RunnerClient
from runner.extract import (
    already_applied,
    extract_fields,
    looks_like_confirmation,
    looks_like_login,
    page_has_captcha,
    page_has_password_input,
    page_text,
)
from runner.fill import apply_instructions, click_first, click_next, set_file_inputs
from runner.live import LiveSession
from runner.terminal_checkpoint import prompt_checkpoint

log = logging.getLogger("kame.runner")


def auto_submit_allowed(run: dict[str, Any]) -> bool:
    """Live auto-submit only when the API policy authorized it for this run."""
    policy = run.get("policy") or {}
    auto = policy.get("auto_submit") or {}
    return (
        bool(auto.get("allow_submit"))
        and bool(policy.get("allow_submit"))
        and not policy.get("platform_no_auto_submit")
    )


async def run_apply(
    *,
    browser: Browser,
    client: RunnerClient,
    run: dict[str, Any],
    runner_id: str,
    headed: bool,
    terminal_checkpoints: bool,
    step_budget: int,
) -> None:
    run_id = str(run["id"])
    url = run["page_url"]
    ats = run.get("ats") or detect_adapter(url).key
    adapter = detect_adapter(url)
    profile_id = str(run.get("profile_id") or "")
    # profile_id may not be on ApplyRunRead — fetch from get_run if missing
    if not profile_id:
        full = client.get_run(run_id)
        # API read may omit profile_id; use policy
        profile_id = str(full.get("profile_id") or "")

    context = await browser.new_context()
    page = await context.new_page()
    resume_tmp: tempfile.TemporaryDirectory | None = None
    resume_path: str | None = None
    seq = int(run.get("last_step_seq") or 0)
    live = LiveSession(
        page=page,
        api_base=client._base,
        token="",
        workspace_id=client._headers.get("X-Workspace-Id", ""),
        run_id=run_id,
        headers=client._headers,
    )
    live.user_edited = {
        str(x.get("field_id"))
        for x in (run.get("user_edited_fields") or [])
        if isinstance(x, dict) and x.get("field_id")
    }

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        client.heartbeat(run_id, runner_id, page.url)
        await live.start()

        for _ in range(step_budget):
            await live.wait_if_human()
            text = await page_text(page)
            fields = await extract_fields(page)

            if already_applied(text):
                client.complete(run_id, runner_id=runner_id, status="completed", confirmation=False)
                return

            if looks_like_confirmation(text, adapter.confirmation_needles) and not fields:
                # Confirmation without our submit means user/site finished.
                client.complete(run_id, runner_id=runner_id, status="completed", confirmation=False)
                return

            if await page_has_captcha(page):
                await live.notify_human_for_checkpoint()
                await _checkpoint(
                    client,
                    run_id,
                    "captcha",
                    {"message": "Solve the challenge"},
                    page,
                    terminal_checkpoints,
                    headed,
                    live=live,
                )
                continue

            if await page_has_password_input(page) or looks_like_login(text, adapter.login_needles):
                await live.notify_human_for_checkpoint()
                await _checkpoint(
                    client,
                    run_id,
                    "login",
                    {"message": f"Sign in to continue on {adapter.key}"},
                    page,
                    terminal_checkpoints,
                    headed,
                    live=live,
                )
                continue

            if not fields:
                await _checkpoint(
                    client,
                    run_id,
                    "blocked",
                    {"message": "No form fields found"},
                    page,
                    terminal_checkpoints,
                    headed,
                    live=live,
                )
                break

            # plan-page needs profile_id — load from application via run policy if needed
            plan_body_profile = profile_id
            if not plan_body_profile:
                # Fall back: open unknown_required for whole page
                await _checkpoint(
                    client,
                    run_id,
                    "blocked",
                    {"message": "Missing profile on run"},
                    page,
                    terminal_checkpoints,
                    headed,
                    live=live,
                )
                break

            plan = client.plan_page(
                run_id=run_id,
                page_url=page.url,
                fields=fields,
                ats=ats,
                profile_id=plan_body_profile,
            )
            instructions = plan.get("instructions") or []
            # Never overwrite fields the user edited during takeover.
            instructions = [
                i for i in instructions if not live.should_skip_field(str(i.get("field_id") or ""))
            ]

            # Raise checkpoints from instructions before filling
            for instr in instructions:
                if instr.get("action") != "checkpoint":
                    continue
                kind = instr.get("checkpoint_kind") or "unknown_required"
                cp = client.open_checkpoint(
                    run_id,
                    kind,
                    {
                        "field_id": instr.get("field_id"),
                        "label": instr.get("note") or instr.get("field_id"),
                        "canonical_key": instr.get("canonical_key"),
                    },
                )
                decision = await _resolve(client, run_id, cp, terminal_checkpoints, headed, page)
                if decision.get("decision") == "cancel":
                    client.complete(run_id, runner_id=runner_id, status="cancelled")
                    return
                if decision.get("decision") == "handoff_extension":
                    return
                if decision.get("decision") == "typed_value" and kind == "sensitive_field":
                    val = client.ephemeral_sensitive(run_id)
                    if val:
                        instr["action"] = "fill"
                        instr["value"] = val

            counts = await apply_instructions(page, instructions)
            filled_n = counts["filled"]

            # Attach the accepted resume once per run when the page asks for a file.
            if resume_path is None and plan.get("resume_upload_url"):
                resume_tmp = tempfile.TemporaryDirectory()
                suffix = Path(str(plan.get("resume_file_name") or "resume.pdf")).suffix or ".pdf"
                resume_path = client.download(
                    str(plan["resume_upload_url"]), str(Path(resume_tmp.name) / f"resume{suffix}")
                )
            if resume_path:
                await set_file_inputs(page, resume_path)

            # Fallback if almost nothing filled
            if filled_n == 0 and any(i.get("action") == "fill" for i in instructions) is False:
                values = {
                    i["canonical_key"]: i["value"]
                    for i in instructions
                    if i.get("canonical_key") and i.get("value")
                }
                await constrained_fill(page, adapter=adapter, values=values, step_budget=5)

            with tempfile.TemporaryDirectory() as td:
                shot = Path(td) / f"step-{seq + 1}.png"
                await screenshot_blurred(page, shot)
                screenshot_b64 = base64.b64encode(shot.read_bytes()).decode("ascii")
                seq += 1
                client.upload_step(
                    run_id,
                    {
                        "seq": seq,
                        "page_url": page.url,
                        "action": "page",
                        "field_label": f"filled={counts['filled']}",
                        "value_redacted": "",
                        "screenshot_b64": screenshot_b64,
                        "outcome": "ok",
                    },
                )
            if live.live_mode == "screenshot":
                await live.push_screenshot()

            client.heartbeat(run_id, runner_id, page.url)

            # Final review when no Next and we see a Submit button
            submit_visible = False
            for sel in adapter.submit_selectors:
                try:
                    if await page.locator(sel).first.is_visible():
                        submit_visible = True
                        break
                except Exception:  # noqa: S112 — try next submit selector
                    continue

            clicked_next = await click_next(page, adapter)
            if clicked_next:
                await page.wait_for_timeout(500)
                continue

            if submit_visible:
                # Live auto-submit: only when the API policy authorized it and submit_approved is
                # recorded. Otherwise always pause for final_review.
                fresh = client.get_run(run_id)
                if auto_submit_allowed(fresh) and fresh.get("submit_approved"):
                    await click_first(page, adapter.submit_selectors)
                    await page.wait_for_timeout(800)
                    ok = looks_like_confirmation(
                        await page_text(page), adapter.confirmation_needles
                    )
                    client.complete(
                        run_id, runner_id=runner_id, status="completed", confirmation=ok
                    )
                    return

                cp = client.open_checkpoint(
                    run_id,
                    "final_review",
                    {
                        "message": "Review answers and approve Submit",
                        "page_url": page.url,
                        "steps": seq,
                    },
                )
                decision = await _resolve(client, run_id, cp, terminal_checkpoints, headed, page)
                if decision.get("decision") == "approve_submit":
                    fresh = client.get_run(run_id)
                    if not fresh.get("submit_approved"):
                        log.error("submit blocked: not approved on server")
                        client.complete(
                            run_id,
                            runner_id=runner_id,
                            status="failed",
                            failure_reason="submit_not_approved",
                        )
                        return
                    if fresh.get("policy", {}).get("platform_no_auto_submit"):
                        client.complete(
                            run_id,
                            runner_id=runner_id,
                            status="failed",
                            failure_reason="platform_no_auto_submit",
                        )
                        return
                    await click_first(page, adapter.submit_selectors)
                    await page.wait_for_timeout(800)
                    text2 = await page_text(page)
                    ok = looks_like_confirmation(text2, adapter.confirmation_needles)
                    client.complete(
                        run_id, runner_id=runner_id, status="completed", confirmation=ok
                    )
                    return
                if decision.get("decision") == "cancel":
                    client.complete(run_id, runner_id=runner_id, status="cancelled")
                    return
                # deny / handoff
                return

            # Stuck
            await _checkpoint(
                client,
                run_id,
                "blocked",
                {"message": "No next/submit control found"},
                page,
                terminal_checkpoints,
                headed,
                live=live,
            )
            break

        client.complete(run_id, runner_id=runner_id, status="failed", failure_reason="step_budget")
    except Exception as exc:
        log.exception("run_failed")
        client.complete(run_id, runner_id=runner_id, status="failed", failure_reason=str(exc)[:200])
    finally:
        await live.close()
        await context.close()
        if resume_tmp is not None:
            resume_tmp.cleanup()


async def _checkpoint(
    client: RunnerClient,
    run_id: str,
    kind: str,
    detail: dict,
    page: Page,
    terminal: bool,
    headed: bool,
    live: LiveSession | None = None,
) -> dict:
    cp = client.open_checkpoint(run_id, kind, detail)
    if live is not None:
        await live.notify_human_for_checkpoint()
    return await _resolve(client, run_id, cp, terminal, headed, page, live=live)


async def _resolve(
    client: RunnerClient,
    run_id: str,
    cp: dict,
    terminal: bool,
    headed: bool,
    page: Page,
    live: LiveSession | None = None,
) -> dict:
    if terminal:
        decision = prompt_checkpoint(cp["kind"], cp.get("detail") or {})
        body = {
            "decision": decision["decision"],
            "value": decision.get("value"),
            "note": decision.get("note"),
        }
        resolved = client.resolve_checkpoint(cp["id"], body)
        if live is not None:
            live.control_mode = "agent"
            live._human_event.set()
        return {"decision": body["decision"], "value": body.get("value"), "raw": resolved}
    # Cloud: wait for web UI resolve (and/or live-view HUMAN actions)
    resolved = client.wait_checkpoint(run_id, cp["id"])
    dec = (resolved.get("decision") or {}).get("decision") or "continue"
    if live is not None:
        live.control_mode = "agent"
        live._human_event.set()
    return {"decision": dec, "raw": resolved}
