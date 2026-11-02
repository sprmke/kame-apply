"""HTTP client for the apply-run pull protocol."""

from __future__ import annotations

from typing import Any

import httpx


class RunnerClient:
    def __init__(self, *, api_base: str, token: str, workspace_id: str) -> None:
        self._base = api_base.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "X-Workspace-Id": workspace_id,
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self._base}/api/v1{path}"

    def claim(self, runner_id: str) -> dict[str, Any] | None:
        r = httpx.post(
            self._url("/runs/runner/claim"),
            headers=self._headers,
            json={"runner_id": runner_id},
            timeout=30.0,
        )
        r.raise_for_status()
        if r.status_code == 204 or not r.content:
            return None
        data = r.json()
        return data if data else None

    def heartbeat(self, run_id: str, runner_id: str, page_url: str | None = None) -> dict:
        r = httpx.post(
            self._url(f"/runs/{run_id}/heartbeat"),
            headers=self._headers,
            json={"runner_id": runner_id, "page_url": page_url},
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()

    def upload_step(self, run_id: str, body: dict[str, Any]) -> dict:
        r = httpx.post(
            self._url(f"/runs/{run_id}/steps"), headers=self._headers, json=body, timeout=30.0
        )
        r.raise_for_status()
        return r.json()

    def open_checkpoint(self, run_id: str, kind: str, detail: dict) -> dict:
        r = httpx.post(
            self._url(f"/runs/{run_id}/checkpoints"),
            headers=self._headers,
            json={"kind": kind, "detail": detail},
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()

    def resolve_checkpoint(self, checkpoint_id: str, decision: dict) -> dict:
        r = httpx.post(
            self._url(f"/runs/checkpoints/{checkpoint_id}/resolve"),
            headers=self._headers,
            json=decision,
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()

    def wait_checkpoint(self, run_id: str, checkpoint_id: str, *, poll: float = 2.0) -> dict:
        import time

        while True:
            r = httpx.get(
                self._url(f"/runs/{run_id}/checkpoints"), headers=self._headers, timeout=30.0
            )
            r.raise_for_status()
            for c in r.json():
                if c["id"] == checkpoint_id and c["status"] != "open":
                    return c
            time.sleep(poll)

    def plan_page(
        self, *, run_id: str, page_url: str, fields: list[dict], ats: str, profile_id: str
    ) -> dict:
        r = httpx.post(
            self._url(f"/runs/{run_id}/plan-page"),
            headers=self._headers,
            json={
                "run_id": run_id,
                "page_url": page_url,
                "platform": ats,
                "fields": fields,
                "profile_id": profile_id,
            },
            timeout=60.0,
        )
        r.raise_for_status()
        return r.json()

    def ephemeral_sensitive(self, run_id: str) -> str | None:
        r = httpx.get(
            self._url(f"/runs/{run_id}/ephemeral-sensitive"),
            headers=self._headers,
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json().get("value")

    def complete(
        self,
        run_id: str,
        *,
        status: str = "completed",
        confirmation: bool = False,
        failure_reason: str | None = None,
        runner_id: str | None = None,
    ) -> dict:
        r = httpx.post(
            self._url(f"/runs/{run_id}/complete"),
            headers=self._headers,
            params={
                "status": status,
                "confirmation": str(confirmation).lower(),
                **({"failure_reason": failure_reason} if failure_reason else {}),
                **({"runner_id": runner_id} if runner_id else {}),
            },
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()

    def get_run(self, run_id: str) -> dict:
        r = httpx.get(self._url(f"/runs/{run_id}"), headers=self._headers, timeout=30.0)
        r.raise_for_status()
        return r.json()
