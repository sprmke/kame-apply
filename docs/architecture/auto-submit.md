# Auto-submit policies (Phase 19)

**Go/no-go:** Live mode stays behind `AUTO_SUBMIT_ENABLED` (default off). Enable only after assist-mode fill accuracy meets the phase gate.

## Policy (every condition must pass)

Allowlisted ATS (not LinkedIn/Indeed/JobStreet), risk green, match score ≥ threshold, free-text answers from approved bank or batch approval, no checkpoint, company + daily caps ok, job open and fresh (≤72h), track autonomy `auto_submit`, track/workspace/global kill switches off.

## Dry-run

First N runs per Track (default 10) fill to final review and record a dry-run report (`would_submit`) without submitting. Live enable requires `dry_run_remaining == 0`.

## Oversight

- Workspace kill: `POST /workspaces/auto-submit/kill`
- Track kill / anomaly pause (failure rate ≥50% over ≥5 runs/24h)
- Explain: `GET /applications/{id}/auto-submit/explain`
- Batch approve: `POST /auto-submit/batch-approve`
- Digest should list auto-submitted apps (Needs-you / activity already surfaces dry-run audit events)
