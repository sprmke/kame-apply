# Research 03: Apply engine, human checkpoints, live view

**Researched:** 2026-10-28 · Feeds into Phases 13, 15, 16, 19.

## 1. Two execution paths, one brain

| | **Extension (in the user's browser)** | **Cloud runner (headless, ours)** |
| --- | --- | --- |
| Where | User's Chrome/Edge/Firefox, their logins, their IP | Playwright Chromium on our VM, or on the user's machine (local runner) |
| Best for | Forms behind the user's own login (Workday accounts, company portals), anything with CAPTCHAs, one-off jobs. LinkedIn/Indeed/JobStreet modes are opt-in per platform policy (plan-critique §2.1) | Company ATS forms without login (Greenhouse, Lever, Ashby, Workable, SmartRecruiters...), batches of prepared applications |
| Who clicks | User is present; extension fills, user reviews and submits | Runner fills; user watches/approves in live view; submits only per autonomy policy |
| Release | **1 (MVP)** | 2 |

Both call the same API: `POST /runs/{id}/plan-page` with the extracted fields → returns fill instructions (value, source fact, confidence, sensitivity, checkpoint reasons). The **field brain lives server-side**, so extension and runner behave identically and improvements reach both.

## 2. The page loop (shared logic)

```
for each page/step of the form:
  1. EXTRACT   fields: label (aria/label/for/placeholder/nearby text), type, options, required, constraints (maxlength),
               section heading, page-level notices (e.g. "do not use AI"), file inputs, custom widgets (Workday/React selects)
  2. CLASSIFY  each field → canonical key (first_name, email, phone, linkedin, work_auth_us, sponsorship, salary, start_date,
               years_experience_<skill>, eeo_*, custom_question...) via (a) ATS adapter map, (b) cached mapping for this
               form signature, (c) rules + synonyms, (d) LLM fallback (batched, cheap model)
  3. SENSITIVITY  public | personal | sensitive(government id, bank, card, full DOB, SSN/TIN, full address pre-offer,
               health/disability details beyond EEO defaults) → sensitive always ⇒ checkpoint
  4. RESOLVE   value from: answer bank → Career Profile facts → tailored resume → drafted answer (needs approval in assist)
               → unknown ⇒ checkpoint(unknown_required) if required, else leave blank
  5. AI-RESTRICTION  if page/field text says not to use AI ⇒ do not draft; checkpoint(ai_restricted), show facts as notes
  6. FILL      deterministic actions (adapter selectors / role-based locators); upload the exact resume version file
  7. VERIFY    read back values, check validation errors, screenshot (sensitive fields blurred)
  8. NEXT      click Next/Continue; detect navigation, errors, login walls, CAPTCHA/challenge ⇒ checkpoint
final: REVIEW checkpoint (summary of every answer) → submit (user, or auto per policy) → detect confirmation → record
```

**Form signature cache (Stagehand idea):** hash of (ATS, normalized field labels). Once a form type is mapped, the mapping is reused across users with no LLM cost. Values are never cached across tenants, only label → canonical-key mappings.

## 3. ATS adapters (deterministic first)

Priority order by volume: Greenhouse, Lever, Ashby, Workday, Workable, SmartRecruiters, iCIMS, SuccessFactors, Taleo, BambooHR, Recruitee, Personio, Teamtailor, JazzHR, Breezy; plus platform modes in the extension: LinkedIn Easy Apply, Indeed Apply, JobStreet/SEEK Quick Apply.

Each adapter: URL detection, page-step model, known field map, custom widget handlers (Workday combo boxes, date pickers, multi-select, React-select), resume upload behavior (some ATSs parse the upload and **prefill** fields, so we must re-verify and correct parsed values), confirmation detection, known quirks. Fixture tests use saved HTML snapshots of real forms (sanitized), run in CI.

**Unknown forms:** generic extractor + LLM mapping; if structure is too dynamic, **browser-use** agent fallback, constrained: allowed actions = fill/select/upload/click-next only, never submit, never navigate off-domain except known SSO; every action logged; max steps; same checkpoint rules.

## 4. Checkpoints (human in the loop)

| Kind | Trigger | User sees | Resume behavior |
| --- | --- | --- | --- |
| `login` | Login form, SSO, "create account" wall | "Log in to {site}" with live view / open in your browser | Session saved encrypted (opt-in) for next time |
| `captcha` | reCAPTCHA/hCaptcha/Turnstile iframe, challenge page, "verify you are human" | "Solve the check" in live view | Continue after the challenge clears (auto-detected) |
| `ai_restricted` | Notice like "do not use AI / ChatGPT", "AI-generated answers will be disqualified", honesty attestations | The question + relevant profile facts as notes; text box; no AI draft | User's text is filled as typed |
| `sensitive_field` | Sensitive classification | Field + why it's sensitive + "this is unusual at application stage" if applicable | User types it in live view/their browser; value **never stored** |
| `unknown_required` | No confident value | Question + suggested answer (if allowed) | Optional save to answer bank |
| `answer_approval` | Drafted free-text answers (assist mode) | All drafts in one review panel; edit/approve | Batch approve |
| `risk` | Job risk yellow/red at preflight or new signals mid-form (e.g. asks for payment) | Risk reasons; Continue anyway / Skip / Report | |
| `final_review` | Before submit | Summary of all answers + resume file + screenshot | User submits (assist) |
| `blocked` | Site error, rate limit, page structure unknown after N tries | What happened; options: retry later / open in your browser (extension takes over) / mark manual | |

**Saved progress:** each step is a DBOS checkpoint + a `run_steps` row. On resume we reopen the URL with the saved session state, detect the current step, and re-verify fields already filled (forms often persist drafts server-side; when they don't, we re-fill from the step log). Handoff to the extension: "Continue in my browser" opens the form in the user's browser and the extension continues from the step log.

**Timeouts:** an unanswered checkpoint never fails the run. After 30 min the browser session is closed to free resources (state saved), and the run sits in `needs_you` until the user returns or the job closes.

## 5. Live view and takeover

Why not an iframe: job sites send `X-Frame-Options`/`frame-ancestors` headers that forbid framing, and cross-origin frames can't be driven or observed anyway.

**Chosen:** CDP screencast relay.

```
runner (Playwright) ──CDP──► Page.startScreencast{format:jpeg, quality:60, maxWidth:1280, everyNthFrame:1}
   frames ─► runner WS ─► API relay (auth: run-scoped token) ─► web client <canvas>
   viewer input (mouse/keys/scroll/paste) ─► API ─► runner ─► Input.dispatchMouseEvent / dispatchKeyEvent / insertText
   control state: AGENT | HUMAN  (agent actions paused while HUMAN has control)
```

- Frame ack (`Page.screencastFrameAck`) throttles to client speed; adaptive quality on slow links; mobile viewers get scaled frames and tap-to-click.
- **Takeover protocol:** user clicks "Take over" → runner pauses the loop at a safe point → control = HUMAN → user acts → "Hand back" → runner re-extracts the page and continues. Checkpoints automatically switch to HUMAN.
- Step sidebar: each filled field with value (redacted if sensitive), source fact link, confidence; click to edit (writes through runner).
- Security: viewers must be workspace members with the run's permission; tokens expire in minutes; sensitive keystrokes in HUMAN mode are not logged; the clipboard is passed only on explicit paste.
- Fallback if WebSocket bandwidth is poor: screenshot-per-step mode (still images every action).
- Replay: per-step screenshots stored with the application (retention configurable, default 90 days).

Evaluated alternatives: noVNC + Xvfb (full desktop, heavier, more bandwidth, less control over input routing); hosted live-view products (Browserbase, Cloudflare Browser Run, Upstash Box: paid at scale, but a fine later option for burst capacity).

## 6. Extension design (Release 1)

- **WXT** MV3, Vue side panel (shared `packages/ui`), content scripts per ATS/platform, background service worker for API calls.
- Auth: user signs in on the web app → app issues an extension token (scoped, revocable) via `externally_connectable` handshake.
- Features: **Clip job** (reads the current job page, sends sanitized text + URL; dedupes with existing jobs); **Autofill** (calls `plan-page`, fills fields with visible highlighting; each filled field shows a small badge with its source; never clicks Submit); **Answer insert** (Answer Desk drafts inserted into the focused field); **Log applied** (detects confirmation page or user clicks "I applied"); **Checkpoint UI** in side panel (same kinds as runner).
- Permissions: minimal host permissions requested per site on first use (`optional_host_permissions`), so the install prompt isn't scary.
- Store review: Chrome Web Store policy requires a clear single purpose and privacy disclosure. Prepare a privacy policy and limited-use statement in Phase 13.
- Platform terms: autofill with the user present and the user clicking Submit is how Simplify, Teal, and others operate. No background navigation on LinkedIn/Indeed/JobStreet; no batch applying there.

## 7. Auto-submit (Release 2+, Phase 19)

Only when every condition in PRD F8 holds. Extra safeguards: dry-run mode (fills to final review, records what would be submitted) for the first N runs per Track; per-company cap; random sample of auto-submitted applications sent to the user for review in the daily digest; kill switch per workspace.

## 8. Failure modes to design for

Multi-page forms that change based on answers · iframes (Workday, embedded Greenhouse on company domains) · shadow DOM · file upload that triggers ATS parsing and overwrites fields · duplicate-application detection by the ATS ("you already applied") · forms that require account creation + email verification (checkpoint `login` + inbox code: user handles) · session expiry mid-run · job closed between discovery and apply · non-English forms (LLM mapping is multilingual; values from profile; language mismatch warning) · conditional required fields · character limits · date/phone format localization · salary fields expecting different currency/period · "How did you hear about us" (answer bank default per source) · EEO/voluntary self-identification (defaults to "decline to self-identify" unless the user chose otherwise) · assessments/quizzes embedded in apply flow (always checkpoint, never answered by AI) · video/voice recording steps (checkpoint, user does it).
