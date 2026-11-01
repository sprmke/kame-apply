"""kame-runner entrypoint: poll claim → run page loop."""

from __future__ import annotations

import asyncio
import logging
import sys

from playwright.async_api import async_playwright

from runner.client import RunnerClient
from runner.config import RunnerSettings
from runner.loop import run_apply

log = logging.getLogger("kame.runner")


async def _loop(settings: RunnerSettings) -> None:
    if not settings.token or not settings.workspace_id:
        log.error("Set KAME_RUNNER_TOKEN and KAME_RUNNER_WORKSPACE_ID")
        sys.exit(2)
    client = RunnerClient(
        api_base=settings.api_base,
        token=settings.token,
        workspace_id=settings.workspace_id,
    )
    sem = asyncio.Semaphore(max(1, settings.max_concurrency))

    async def _one(browser, run: dict) -> None:
        async with sem:
            log.info("claimed run=%s ats=%s url=%s", run["id"], run.get("ats"), run.get("page_url"))
            await run_apply(
                browser=browser,
                client=client,
                run=run,
                runner_id=settings.runner_id,
                headed=settings.headed,
                terminal_checkpoints=settings.terminal_checkpoints and settings.mode == "local",
                step_budget=settings.step_budget,
            )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not settings.headed)
        tasks: set[asyncio.Task] = set()
        try:
            while True:
                done = {t for t in tasks if t.done()}
                for t in done:
                    tasks.discard(t)
                    exc = t.exception()
                    if exc:
                        log.error("run_task_failed: %s", exc)
                if len(tasks) >= settings.max_concurrency:
                    await asyncio.sleep(settings.poll_seconds)
                    continue
                run = client.claim(settings.runner_id)
                if not run:
                    await asyncio.sleep(settings.poll_seconds)
                    continue
                tasks.add(asyncio.create_task(_one(browser, run)))
        finally:
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            await browser.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = RunnerSettings()
    if settings.mode == "local" and not any(a.startswith("--") for a in sys.argv[1:]):
        settings.headed = True
    asyncio.run(_loop(settings))


if __name__ == "__main__":
    main()
