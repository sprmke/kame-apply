# Security review: Phase 2

`security-auditor` reviewed auth, tenancy and RLS, AI credentials and the web client on 2026-11-01. No critical findings. Each item below is either fixed with a regression test (`apps/api/tests/test_security_hardening.py`) or accepted with a reason and an owner phase.

## Fixed

| # | Finding | Fix |
| --- | --- | --- |
| H1 | Pre-hijack: an attacker registers a victim's email unverified, links their Google identity, and keeps access after the victim resets the password | Linking needs a verified email; an identity cannot sign in to an unverified account; unlink endpoint (`DELETE /auth/google/link`, refused for Google-only accounts) |
| M1 | Ollama URL SSRF: CGNAT passed, redirects followed, DNS checked once, any port | Non-global addresses blocked (incl. IPv4-mapped IPv6), port allowlist, re-validated at call time off the event loop, redirects disabled on the client |
| M2 | Fail-open: unset `ENVIRONMENT` ran with public dev secrets | Default is now `prod`; dev secrets only work with an explicit `local` or `test` |
| M3 | Multi-tab refresh race cleared the winner's cookie | The race answers 401 without touching the cookie |
| M4 | Invite email binding bypassed by registering the invited address unverified | Accepting an invitation needs a verified email |
| M5 | Invitation flooding as a mail relay | Inviter must be verified; 20 per user and 30 per workspace per hour |
| M7 | Argon2 blocked the event loop | Hash and verify run in a worker thread |
| M8 | Per-email login limit let a stranger lock a victim out | Tight cap per (email, IP), loose per-email cap |
| M9 | Secrets in Sentry locals and SQLAlchemy error parameters | `include_local_variables=False`, `hide_parameters=True` |
| M10 | Dev read-only role could read tenant tables by setting the RLS variables itself | Migration 0007 revokes them; test checks every sensitive table |
| L1 | Keys of 4 characters or fewer stored in the clear as the hint | Minimum key length 8 |
| L2 | Concurrent Google sign-up gave a 500 | `ON CONFLICT` and the `account_exists` redirect |
| L3 | Rolling refresh kept a stolen session alive forever | 90 day absolute session age |
| L4 | Tokens in URLs could leak through `Referer` | `Referrer-Policy: no-referrer` (API headers and a meta tag), plus `nosniff` |

## Accepted

| # | Finding | Why | Revisit |
| --- | --- | --- | --- |
| M6 | Register returns 409 for a known email; forgot-password timing differs when the account exists | Clear sign-up errors matter more than hiding existence at this stage; rate limited. Mail is sent inline so tests are deterministic | Move sending to a background task and make register uniform when abuse shows up (Phase 14) |
| M8 | Rate limits are per process and key on the socket address | Single free-tier instance. Behind a proxy the address is the proxy | Phase 14: trusted forwarded-IP header, and Postgres-backed limits before a second instance |
| M11 | The AI budget is a soft cap: no lock between check and write, the ledger row rolls back with a failing request, failed billed calls record nothing | Nothing calls `run_text` yet. Workflows (DBOS steps) will own their transactions | Phase 3 first caller: reserve an estimate under an advisory lock, write the ledger in its own step |
| L5 | Raw SQL as the app role could delete its own membership rows in other workspaces, and RLS does not enforce roles | RBAC is enforced in the service layer by design; raw SQL is not reachable from the API | Split SELECT and write policies if a second writer ever appears |
| L6 | KEK rewrap does not re-verify the new wrap; the API has no `MASTER_KEK_PREVIOUS` fallback; ciphertext AAD does not bind the credential id | Rotation is an operator procedure with an outage window; same-workspace swaps need DB write access | Before the first prod deploy: add a post-wrap check and a previous-key fallback |
| - | Reset, verify and invite tokens stay in the URL after the page reads them | Referrer is now suppressed; stripping adds history complexity | Optional polish |
| - | PydanticAI deprecation warning for `httpx.AsyncClient` on OpenAI-compatible providers | Needed to disable redirects | Move to the replacement client when PydanticAI v3 lands |

## Checked and sound

JWT verification and live-session checks; refresh token storage, rotation and reuse revocation; password hashing and reset; OAuth state and PKCE; no open redirects; access token held in memory; no `v-html`; workspace context ordering and uniform 404; RLS forced on every tenant table; append-only audit and usage ledgers; RBAC rank rules and last-owner protection; envelope encryption and no key exposure in responses, logs or audit rows; tool-less LLM calls.
