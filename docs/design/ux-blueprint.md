# UX blueprint

**Status:** Planned · **Last updated:** 2026-10-28 · Implemented across Phases 2–16. Visual language: [`design-system.md`](./design-system.md) ("Field Notes"). Kame Apply has its own identity and doesn't reuse other Kame apps' layouts or components.

## 1. UX principles

1. **Time to first value under 5 minutes:** upload resume → confirm → first Track → first real matches and a resume critique, in one sitting.
2. **"Needs you" is the center of gravity.** Automation creates work only when a human is truly needed; that work is always one tap away and never lost.
3. **Explain every AI decision** with proof marks: why this job matched, why it's flagged, why a resume line changed, which fact a filled field came from.
4. **Pencil, then ink:** AI output is drafted in pencil and becomes ink only when the user accepts it. Nothing irreversible happens silently.
5. **Read first:** postings and resumes get the widest, best-typeset column; actions live in a consistent context panel.
6. **Mobile is first-class for decisions** (triage, approvals, checkpoints, live runs). Heavy editing works on mobile but is optimized for desktop.
7. **Accessible:** WCAG 2.2 AA, keyboard-complete, screen-reader labels, reduced motion, color never the only signal.
8. **Copy:** minimal and human (`ui-minimal-copy`, `human-copy` rules); explanations are short sentences, never marketing.

## 2. Information architecture and navigation

```
Desk sidebar (208px)                 Top of content area
──────────────────────               ─────────────────────────────────────────────────────
◉ Today              (badge)         Workspace switcher · Search · profile
▤ Searches
⌕ Jobs                (Reader)
▣ Applications        (Reader + board)
◯ Profile
  More tools (collapsed)
    Resume studio · Answer help · Practice · Replies · Contacts · Safety
⚙ Settings
```

- **Today:** guided brief (see §3.1). One next step, then new matches, then searches.
- **Searches (Tracks internally):** saved role searches. Inside a search: matches, history, and search settings. The top-level label is plain language; the API and database keep `Track`.
- **Jobs / Applications / Studio** use the **Reader** layout (list · document · context panel).
- **Profile:** Career Profile · Answer bank · Voice · Documents · Links · Be Found [R2]. Resume Studio is linked here.
- **Settings:** workspace · members · AI providers & routing (incl. "My Claude") · notifications · integrations (extension, email alerts, Telegram, Claude) · data export/delete.
- **More tools:** Replies, Resume studio, Answer help, Practice, Contacts, Safety. These are not primary navigation.
- **Mobile:** bottom bar **Today · Searches · Jobs · Applications · More**; Reader panes become stacked screens with a sticky action bar; sheets replace dialogs; swipe right = shortlist, left = skip on job cards.

## 3. Key screens

### 3.1 Today (guided brief, not a dashboard)

- **One next step** in a paper card: add a resume, start a search, run the first search, or review matches. The card names the action and why.
- **Headline sentence** in Newsreader: "227 matches across 1 search. Nothing needs you." Use "matches", not "strong matches", until relevance earns it.
- **New matches:** the top three with title, company, score, one reason, and risk seal. "View all" goes to the search's Jobs view.
- **Your searches:** one card per search with match and shortlist counts, and **View matches**.
- **Needs you** stack: checkpoints, answer approvals, tailoring drafts ready, risk decisions, failed runs, budget alerts. Shown only when something needs a decision.
- **This week:** submitted, response rate, interviews, and matched, collapsed under a disclosure. Not the first screen.
- **Empty state (new user):** contour motif + three setup steps (AI key → resume → search). The first action is the resume, not a dashboard tour.

### 3.2 Jobs (Reader)

- **List pane:** compact rows: score, title, company, eligibility, salary, posted, risk seal; grouped "New since your last visit"; sort (best match / newest / salary); quick filters; saved views; bulk select.
- **Document pane:** the posting typeset in Newsreader, qualifications highlighted inline with proof marks, sanitized; header with company, location/eligibility, salary, sources, original link.
- **Context panel:** match score + reasons, **fit ledger** (must / preferred / knockout with verdicts), risk seal + reasons, company (other open roles), actions: **Tailor resume** · **Apply with extension** · **Apply with runner** [R2] · **Answer Desk** · **Mark applied** · Shortlist / Skip (reason) / Hide company.
- Keyboard: `j/k` move, `s` shortlist, `x` skip, `t` tailor, `o` open original, `?` help.

### 3.3 Criteria builder (see §4)

### 3.4 Studio (Workbench)

- **Critique:** category scores + top 5 fixes; each fix jumps to the line.
- **Pencil diff editor:** proposed changes in pencil with reason + proof mark; accept/reject per change or all; inline "ask me for a metric" prompts write back to the profile.
- **Preview:** live PDF; toggles **Skim view** (7-second zone) and **Parse view** (what an ATS extracts).
- **Insights:** demand chart (have-shown / have-not-shown / adjacent / gap), trends, sample size + confidence, salary range, common titles; "Add to resume" on have-not-shown items.

### 3.5 Tailor for a job (MVP centerpiece, Workbench)

Fit ledger with before → after verdicts (left) · pencil diff of the resume (center) · preview with **grade ring** `C → A-` (right). On mobile: tabs Ledger / Changes / Preview. Footer: **Accept & attach to application** · Edit · Discard. Gaps listed honestly with options (address adjacent experience, add a true missing fact, consider skipping). Knockout panel. Cover letter tab.

### 3.6 Applications (Reader + board)

List with route line per row; optional board view by waypoint; filters by Track/status/date/method. **Dossier** (document pane): folder-tab header, full route line with dates, frozen posting, resume and cover letter sent, answers, run replay screenshots, emails, notes, reminders, outcome.

### 3.7 Answer Desk

Paste area (multi-question detection) or captured questions from the extension → drafts in pencil with copy, char counter vs limit, tone controls; AI-restricted items as "write this yourself" boxes with fact notes; "Save to answer bank".

### 3.8 Live window [R2]

Canvas + Martian Mono step log + control pill **AGENT ⇄ YOU** + Pause / Cancel / Open in my browser; checkpoint banners over the canvas. Mobile: full-width canvas, step log in a bottom sheet.

### 3.9 Safety

Flagged jobs with risk seals and decisions; "Check this" tool (paste message/URL/repo).

## 4. Criteria builder decision

The brief asked: many UI controls, a text area, or AI-generated prompts? **A hybrid, with one structured model underneath.**

```
┌ Describe what you're looking for ───────────────────────────────────────────┐
│ "Senior React or full-stack roles, remote from PH or APAC hours, ≥$4k/mo,    │
│  no crypto, no agencies, product companies"                       [Update]  │
└─────────────────────────────────────────────────────────────────────────────┘
 ROLES     [Senior Frontend Engineer ×] [Full-Stack Engineer ×] ┊ suggested: UI Engineer
 SKILLS    must [React ×][TypeScript ×] · nice [Node.js ×][PostgreSQL ×] · exclude [Angular ×]
 WHERE     Remote ✓ · eligible from [Philippines ×][APAC ×] · timezone overlap ≥ 4h
 PAY       ≥ 4,000 USD / month · ☐ hide jobs without salary
 COMPANY   exclude industries [Crypto ×] · no agencies ✓ · size any
 ▸ More filters (seniority, type, language, visa, education, posting age, keywords…)
 ─────────────────────────────────────────────────────────────────────────────
 Preview  ~240 matches in the last 30 days · 18 new this week     [sample ▾]
 Suggestions  Add "Product Engineer" (+31) · Exclude "WordPress" (−40 noise)
```

- One structured `criteria` JSON is the source of truth. The text box compiles into it and shows the changes as a pencil diff ("added: no agencies"); editing chips regenerates the summary sentence. Either mode works.
- **Templates** per occupation (ESCO/O*NET + curated), e.g. "Registered Nurse – night shift – Dubai".
- Every control defaults to "Any"; only Roles is required.
- **Live preview count** (debounced); zero-result states suggest which filter to relax.
- Thin-coverage countries are stated plainly with "Add email alerts / use the extension" actions (research/02 §4).

## 5. Key flows

1. **Onboarding:** sign up → workspace created → upload resume (or paste / LinkedIn PDF) → parse review (side by side; low-confidence fields first) → quick answer-bank questions (work authorization, location, salary, notice) → first Track (template or describe) → first discovery runs live ("Checked 412 company boards… 37 matches") → land on Track Jobs with a "Critique my resume" prompt → offer the extension and Claude connection.
2. **Daily loop (phone-friendly):** notification "8 strong new matches" → Jobs list → shortlist 3 → tailor each (accept the pencil diff) → apply with the extension on desktop later, or the runner [R2] → approve answers → submit.
3. **Checkpoint:** push "Needs you: CAPTCHA on Acme application" → live window → solve → hand back → run continues → final review → submit.
4. **Scam warning:** Danger seal → reasons with proof marks → **Skip** (default focus) or **Continue anyway** (confirm restates the specific risk).
5. **Manual site:** Answer Desk + extension autofill for standard fields → user submits → extension logs the application.

## 6. States and edge cases every screen must handle

Empty (first use; filtered to zero), loading (skeleton rows and document placeholders, not spinners), partial data (no salary or location), error (plain words + retry), offline (PWA read-only cache of applications and Needs-you), long text (truncation with full text on hover/tap), RTL/CJK postings (document pane respects `dir` and fonts fall back cleanly), many Tracks (Track switcher scrolls + search), large lists (virtualized), permission-limited roles (viewer sees, can't act), stale data ("checked 3h ago").

## 7. Responsive rules

Tested at 375 (phone), 820 (tablet), 1440 (desktop) × light/dark. Reader: 3 panes ≥ 1280px; 2 panes + overlay context 768–1279px; stacked screens < 768px. Workbench: 3 columns → tabs under 1024px. Touch targets ≥ 44px; sticky bottom action bar on mobile; no horizontal page scroll.

## 8. Visual direction

See [`design-system.md`](./design-system.md): warm paper and ink, persimmon accent, Instrument Sans / Newsreader / Martian Mono, Phosphor icons, contour motif, proof marks, pencil→ink drafts, route lines, risk seals, dossiers.
