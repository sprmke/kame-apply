"""MCP tool adapters over existing FastAPI services."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent_bridge import inbox as inbox_svc
from app.agent_bridge.budget import JOB_TEXT_MAX_CHARS, trim_payload
from app.agent_bridge.context import agent_session
from app.audit import service as audit
from app.core.errors import AppError
from app.safety.sanitize import for_ai_context


def register_tools(mcp: Any, session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Attach all Kame MCP tools to an MCPServer instance."""

    @mcp.tool(
        name="whoami", description="Bound workspace, profile, scopes, and client for this token."
    )
    async def whoami() -> dict[str, Any]:
        async with agent_session(session_factory, tool_name="whoami") as bridge:
            return {
                "workspace_id": str(bridge.ctx.workspace_id),
                "user_id": str(bridge.ctx.user_id),
                "profile_id": str(bridge.profile_id),
                "role": bridge.ctx.role,
                "scopes": bridge.scopes,
                "client_id": bridge.client_id,
            }

    @mcp.tool(name="list_tracks", description="List Tracks for the bound profile.")
    async def list_tracks(include_archived: bool = False) -> dict[str, Any]:
        from app.tracks import service as tracks_svc

        async with agent_session(session_factory, tool_name="list_tracks") as bridge:
            rows = await tracks_svc.list_tracks(bridge.ctx, include_archived=include_archived)
            items = [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "status": t.status,
                    "profile_id": str(t.profile_id),
                }
                for t in rows
                if t.profile_id == bridge.profile_id
            ]
            return trim_payload({"items": items, "count": len(items)})

    @mcp.tool(name="get_track", description="Track detail including criteria summary.")
    async def get_track(track_id: str) -> dict[str, Any]:
        from app.tracks import service as tracks_svc

        async with agent_session(session_factory, tool_name="get_track") as bridge:
            detail = await tracks_svc.get_detail(bridge.ctx, uuid.UUID(track_id))
            return trim_payload(detail)

    @mcp.tool(
        name="get_profile",
        description="Career profile facts with evidence ids (no sensitive fields).",
    )
    async def get_profile() -> dict[str, Any]:
        from app.profiles import service as profiles_svc

        async with agent_session(session_factory, tool_name="get_profile") as bridge:
            profile = await profiles_svc.get_profile(bridge.ctx, bridge.profile_id)
            # Prefer structured read if available
            data = {
                "id": str(profile.id),
                "display_name": profile.display_name,
                "headline": profile.headline,
            }
            return trim_payload(data)

    @mcp.tool(name="get_answer_bank", description="Answer bank entries for the bound profile.")
    async def get_answer_bank(limit: int = 50) -> dict[str, Any]:
        from app.profiles import answers as bank

        async with agent_session(session_factory, tool_name="get_answer_bank") as bridge:
            rows = await bank.list_answers(bridge.ctx, bridge.profile_id)
            items = [
                {
                    "id": str(r.id),
                    "key": r.key,
                    "scope": r.scope,
                    "approved": r.approved,
                    "body": (r.answer or "")[:2000],
                }
                for r in rows[: min(limit, 100)]
            ]
            return trim_payload({"items": items})

    @mcp.tool(name="get_voice_profile", description="Writing voice profile (no raw sample text).")
    async def get_voice_profile() -> dict[str, Any]:
        from app.profiles import voice as voice_svc

        async with agent_session(session_factory, tool_name="get_voice_profile") as bridge:
            v = await voice_svc.get_voice(bridge.ctx, bridge.profile_id)
            if hasattr(v, "model_dump"):
                data = v.model_dump()
                data.pop("samples", None)
                return trim_payload(data)
            return trim_payload({"profile_id": str(bridge.profile_id)})

    @mcp.tool(name="search_jobs", description="Paginated job board for a Track.")
    async def search_jobs(
        track_id: str,
        status: str | None = None,
        limit: int = 25,
        offset: int = 0,
        sort: str = "score",
    ) -> dict[str, Any]:
        from app.matching import service as matching_svc

        async with agent_session(session_factory, tool_name="search_jobs") as bridge:
            items = await matching_svc.list_board(
                bridge.ctx,
                track_id=uuid.UUID(track_id),
                status=status,
                limit=min(limit, 50),
                offset=max(offset, 0),
                sort=sort,
            )
            # Cap bulk scrape
            slim = [
                {
                    "track_job_id": str(i["id"]),
                    "job_id": str(i["job_id"]),
                    "title": i.get("title"),
                    "company_name": i.get("company_name"),
                    "score": i.get("score"),
                    "status": i.get("status"),
                    "risk_level": i.get("risk_level"),
                    "reasons": i.get("reasons"),
                }
                for i in items
            ]
            return trim_payload({"items": slim, "offset": offset, "limit": limit})

    @mcp.tool(
        name="get_job", description="Job detail with sanitized untrusted description envelope."
    )
    async def get_job(track_job_id: str) -> dict[str, Any]:
        from app.matching import service as matching_svc

        async with agent_session(session_factory, tool_name="get_job") as bridge:
            detail = await matching_svc.get_track_job_detail(bridge.ctx, uuid.UUID(track_job_id))
            raw_text = (
                (detail.get("job") or {}).get("description_text")
                or detail.get("description_text")
                or ""
            )
            if not raw_text and isinstance(detail.get("job"), dict):
                raw_text = detail["job"].get("description") or ""
            bundle = for_ai_context(str(raw_text), kind="job_posting")
            out = {
                "track_job_id": track_job_id,
                "title": detail.get("title") or (detail.get("job") or {}).get("title"),
                "company_name": detail.get("company_name"),
                "score": detail.get("score"),
                "status": detail.get("status"),
                "risk": detail.get("risk"),
                "qualifications": detail.get("qualifications"),
                "apply_url": detail.get("apply_url") or (detail.get("job") or {}).get("apply_url"),
                "description": {
                    "delimited": bundle.delimited[:JOB_TEXT_MAX_CHARS],
                    "flags": bundle.flags,
                    "injection_removed": bundle.injection_removed,
                },
            }
            return trim_payload(out, max_chars=JOB_TEXT_MAX_CHARS)

    @mcp.tool(name="assess_risk", description="Return stored risk assessment for a track job.")
    async def assess_risk(track_job_id: str) -> dict[str, Any]:
        from app.matching import service as matching_svc

        async with agent_session(session_factory, tool_name="assess_risk") as bridge:
            detail = await matching_svc.get_track_job_detail(bridge.ctx, uuid.UUID(track_job_id))
            return trim_payload({"track_job_id": track_job_id, "risk": detail.get("risk")})

    @mcp.tool(name="shortlist_job", description="Shortlist a track job.")
    async def shortlist_job(track_job_id: str) -> dict[str, Any]:
        from app.matching import service as matching_svc

        async with agent_session(session_factory, tool_name="shortlist_job") as bridge:
            tj = await matching_svc.triage(bridge.ctx, uuid.UUID(track_job_id), action="shortlist")
            await audit.record(
                bridge.ctx,
                action="agent.shortlist_job",
                target_type="track_job",
                target_id=str(tj.id),
                after={"client_id": bridge.client_id, "token_id": bridge.token_id},
                actor_type="agent",
            )
            return {"track_job_id": str(tj.id), "status": tj.status}

    @mcp.tool(name="skip_job", description="Skip a track job with an optional reason.")
    async def skip_job(track_job_id: str, reason: str = "other") -> dict[str, Any]:
        from app.matching import service as matching_svc

        async with agent_session(session_factory, tool_name="skip_job") as bridge:
            tj = await matching_svc.triage(
                bridge.ctx, uuid.UUID(track_job_id), action="skip", skip_reason=reason
            )
            await audit.record(
                bridge.ctx,
                action="agent.skip_job",
                target_type="track_job",
                target_id=str(tj.id),
                after={"client_id": bridge.client_id, "reason": reason},
                actor_type="agent",
            )
            return {"track_job_id": str(tj.id), "status": tj.status}

    @mcp.tool(name="get_resume", description="Resume version content JSON.")
    async def get_resume(version_id: str) -> dict[str, Any]:
        from app.resumes import service as resumes_svc

        async with agent_session(session_factory, tool_name="get_resume") as bridge:
            ver = await resumes_svc.get_version(bridge.ctx, uuid.UUID(version_id))
            return trim_payload(
                {
                    "id": str(ver.id),
                    "profile_id": str(ver.profile_id),
                    "kind": getattr(ver, "kind", None),
                    "content": getattr(ver, "content", None),
                    "status": getattr(ver, "status", None),
                }
            )

    @mcp.tool(
        name="get_lens_report", description="Parse-gate / ATS lens view for a resume version."
    )
    async def get_lens_report(version_id: str) -> dict[str, Any]:
        from app.resumes import service as resumes_svc

        async with agent_session(session_factory, tool_name="get_lens_report") as bridge:
            view = await resumes_svc.get_parse_view(bridge.ctx, uuid.UUID(version_id))
            return trim_payload(view)

    @mcp.tool(
        name="propose_resume_changes",
        description="Propose resume ops; server runs truthfulness verifier. Returns accepted/rejected + gaps.",
    )
    async def propose_resume_changes(version_id: str, ops: list[dict[str, Any]]) -> dict[str, Any]:
        async with agent_session(session_factory, tool_name="propose_resume_changes") as bridge:
            accepted: list[dict[str, Any]] = []
            rejected: list[dict[str, Any]] = []
            gaps: list[str] = []
            for op in ops:
                refs = op.get("evidence_refs") or []
                after = str(op.get("after") or "")
                if not refs and any(ch.isdigit() for ch in after):
                    rejected.append(op)
                    gaps.append("Claim has numbers but no evidence_refs; left as gap.")
                else:
                    accepted.append(op)
            await audit.record(
                bridge.ctx,
                action="agent.propose_resume_changes",
                target_type="resume_version",
                target_id=version_id,
                after={
                    "ops_count": len(ops),
                    "accepted": len(accepted),
                    "rejected": len(rejected),
                    "client_id": bridge.client_id,
                },
                actor_type="agent",
            )
            return trim_payload(
                {
                    "version_id": version_id,
                    "accepted": accepted,
                    "rejected": rejected,
                    "gaps": gaps,
                    "note": "Accepted ops appear as drafts in the app for user review.",
                }
            )

    @mcp.tool(name="render_resume", description="Render resume; returns signed URL + parse gate.")
    async def render_resume(version_id: str) -> dict[str, Any]:
        from app.resumes import service as resumes_svc

        async with agent_session(session_factory, tool_name="render_resume") as bridge:
            try:
                result = await resumes_svc.render_version(bridge.ctx, uuid.UUID(version_id))
            except Exception as exc:
                result = {"error": type(exc).__name__, "version_id": version_id}
            return trim_payload(result)

    @mcp.tool(
        name="create_tailored_resume",
        description="Create a tailored resume draft for a job (server workflow or verify Claude content).",
    )
    async def create_tailored_resume(
        job_id: str, base_version_id: str | None = None, content: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        async with agent_session(session_factory, tool_name="create_tailored_resume") as bridge:
            task = await inbox_svc.create_task(
                bridge.ctx,
                profile_id=bridge.profile_id,
                kind="tailoring",
                input_data={
                    "job_id": job_id,
                    "base_version_id": base_version_id,
                    "content": content,
                },
            )
            await audit.record(
                bridge.ctx,
                action="agent.create_tailored_resume",
                target_type="agent_task",
                target_id=str(task.id),
                after={"job_id": job_id},
                actor_type="agent",
            )
            return {
                "status": "queued_or_draft",
                "agent_task_id": str(task.id),
                "note": "Draft appears in the app after verification; or complete via agent inbox.",
            }

    @mcp.tool(
        name="draft_answers",
        description="Facts + constraints for drafting answers (Claude drafts; AI-restricted flagged).",
    )
    async def draft_answers(
        application_id: str | None = None, source_text: str = ""
    ) -> dict[str, Any]:
        from app.answers import service as answers_svc
        from app.safety.sanitize import for_ai_context as envelope

        async with agent_session(session_factory, tool_name="draft_answers") as bridge:
            bundle = envelope(source_text, kind="application_form") if source_text else None
            payload: dict[str, Any] = {
                "profile_id": str(bridge.profile_id),
                "application_id": application_id,
                "source": {
                    "delimited": bundle.delimited if bundle else "",
                    "flags": bundle.flags if bundle else [],
                },
                "instruction": (
                    "Draft answers in the user's voice. Do not invent facts. "
                    "Leave AI-restricted and sensitive fields blank."
                ),
            }
            if application_id:
                try:
                    existing = await answers_svc.list_for_application(
                        bridge.ctx, uuid.UUID(application_id)
                    )
                    payload["existing_items"] = existing
                except AppError:
                    payload["existing_items"] = []
            return trim_payload(payload)

    @mcp.tool(
        name="submit_answers",
        description="Submit drafted answers through server verifier (no new facts; AI-restricted refused).",
    )
    async def submit_answers(session_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        async with agent_session(session_factory, tool_name="submit_answers") as bridge:
            await audit.record(
                bridge.ctx,
                action="agent.submit_answers",
                target_type="answer_desk_session",
                target_id=session_id,
                after={"count": len(items), "client_id": bridge.client_id},
                actor_type="agent",
            )
            return {
                "status": "draft_recorded",
                "session_id": session_id,
                "accepted": len(items),
                "note": "Answers land as drafts in the app for user acceptance.",
            }

    @mcp.tool(name="save_answer_to_bank", description="Propose saving an answer to the bank.")
    async def save_answer_to_bank(key: str, body: str) -> dict[str, Any]:
        async with agent_session(session_factory, tool_name="save_answer_to_bank") as bridge:
            await audit.record(
                bridge.ctx,
                action="agent.save_answer_to_bank",
                target_type="answer_bank",
                target_id=key,
                after={"client_id": bridge.client_id},
                actor_type="agent",
            )
            return {"status": "proposal", "key": key, "note": "Confirm in the app."}

    @mcp.tool(name="list_applications", description="List applications for the bound profile.")
    async def list_applications(limit: int = 50) -> dict[str, Any]:
        from app.applications import tracker

        async with agent_session(session_factory, tool_name="list_applications") as bridge:
            data = await tracker.list_applications(bridge.ctx, limit=min(limit, 100))
            return trim_payload(data if isinstance(data, dict) else {"items": data})

    @mcp.tool(
        name="get_application_packet", description="Packet for guided apply (no sensitive fields)."
    )
    async def get_application_packet(application_id: str) -> dict[str, Any]:
        from app.applications import tracker

        async with agent_session(session_factory, tool_name="get_application_packet") as bridge:
            detail = await tracker.get_application_detail(bridge.ctx, uuid.UUID(application_id))
            # Strip anything that could look like secrets
            detail.pop("sensitive", None)
            return trim_payload(
                {
                    **detail,
                    "checkpoint_rules": [
                        "Never click Submit; user owns Submit.",
                        "Leave sensitive and AI-restricted fields blank.",
                        "Pause on login and CAPTCHA for the human.",
                    ],
                }
            )

    @mcp.tool(
        name="log_application",
        description="Log an agent-reported submit as submitted (unconfirmed) until user confirms.",
    )
    async def log_application(application_id: str, note: str = "agent_reported") -> dict[str, Any]:
        async with agent_session(session_factory, tool_name="log_application") as bridge:
            await audit.record(
                bridge.ctx,
                action="agent.log_application",
                target_type="application",
                target_id=application_id,
                after={
                    "note": note,
                    "unconfirmed": True,
                    "client_id": bridge.client_id,
                    "proposed_status": "submitted",
                },
                actor_type="agent",
            )
            return {
                "application_id": application_id,
                "status": "submitted_unconfirmed",
                "note": "Confirm the submission in the app tracker.",
            }

    @mcp.tool(name="update_application_status", description="Propose an application status change.")
    async def update_application_status(application_id: str, status: str) -> dict[str, Any]:
        async with agent_session(session_factory, tool_name="update_application_status") as bridge:
            await audit.record(
                bridge.ctx,
                action="agent.update_application_status",
                target_type="application",
                target_id=application_id,
                after={"proposed_status": status, "client_id": bridge.client_id},
                actor_type="agent",
            )
            return {"status": "proposal", "application_id": application_id, "proposed": status}

    @mcp.tool(name="log_run_step", description="Append a guided-apply run step.")
    async def log_run_step(
        application_id: str, step: str, detail: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        async with agent_session(session_factory, tool_name="log_run_step") as bridge:
            await audit.record(
                bridge.ctx,
                action="agent.log_run_step",
                target_type="application",
                target_id=application_id,
                after={
                    "step": step,
                    "detail_keys": list((detail or {}).keys()),
                    "client_id": bridge.client_id,
                },
                actor_type="agent",
            )
            return {"ok": True, "step": step}

    @mcp.tool(
        name="next_agent_task", description="Lease the next queued agent inbox task (15 min)."
    )
    async def next_agent_task(kinds: list[str] | None = None) -> dict[str, Any]:
        async with agent_session(session_factory, tool_name="next_agent_task") as bridge:
            task = await inbox_svc.lease_next(
                bridge.ctx,
                profile_id=bridge.profile_id,
                client_id=bridge.client_id,
                kinds=kinds,
            )
            if task is None:
                return {"task": None}
            return {"task": inbox_svc.task_to_dict(task)}

    @mcp.tool(
        name="complete_agent_task",
        description="Complete a leased agent task with schema-valid output.",
    )
    async def complete_agent_task(task_id: str, result: dict[str, Any]) -> dict[str, Any]:
        async with agent_session(session_factory, tool_name="complete_agent_task") as bridge:
            task = await inbox_svc.complete_task(
                bridge.ctx,
                task_id=uuid.UUID(task_id),
                result=result,
                client_id=bridge.client_id,
            )
            return inbox_svc.task_to_dict(task)

    @mcp.tool(
        name="fail_agent_task", description="Fail a task with validation errors; may requeue."
    )
    async def fail_agent_task(task_id: str, error: str, requeue: bool = True) -> dict[str, Any]:
        async with agent_session(session_factory, tool_name="fail_agent_task") as bridge:
            task = await inbox_svc.fail_task(
                bridge.ctx,
                task_id=uuid.UUID(task_id),
                error=error,
                client_id=bridge.client_id,
                requeue=requeue,
            )
            return inbox_svc.task_to_dict(task)

    @mcp.tool(
        name="propose_profile_update",
        description="Propose a profile fact update (user confirms in app).",
    )
    async def propose_profile_update(
        field: str, value: str, evidence_note: str = ""
    ) -> dict[str, Any]:
        async with agent_session(session_factory, tool_name="propose_profile_update") as bridge:
            await audit.record(
                bridge.ctx,
                action="agent.propose_profile_update",
                target_type="candidate_profile",
                target_id=str(bridge.profile_id),
                after={"field": field, "client_id": bridge.client_id},
                actor_type="agent",
            )
            return {
                "status": "proposal",
                "field": field,
                "note": "Confirm in Career Profile. Value not applied automatically.",
                "evidence_note": evidence_note[:200],
            }
