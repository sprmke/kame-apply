# Route: `/start` (set up from a resume)

**Page:** `apps/web/app/pages/start.vue` · **Layout:** `default` · **Access:** signed in with `data.write`

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Resume | Pending | 200+ characters for paste; file type and text extraction by the API | Documented | PDF, DOCX, TXT, MD; one file or pasted text |
| Reading | Pending | n/a | Documented | Polls the draft every 1.5 s; safe to leave |
| Check | Pending | per-row targets validated by the API | Documented | Groups, source chips, needs-you rows, autosave |
| AI | Pending | n/a | Documented | Only when AI is off; explains what AI adds |
| Done | Pending | n/a | Documented | Lands on the first search or the profile |

## Behavior

The page starts a server draft and reviews it. Nothing is saved to the profile, answers, or searches until **Use these** succeeds.

1. **Your resume**: choose a PDF, Word, TXT, or MD file, or paste text (200 characters minimum). An optional sentence says what role comes next. The AI line says whether the full work history will be read. **Start blank** goes to Searches, where a search is created by hand.
2. **Reading**: the draft runs on the server. The list shows plain step names and their state. Leaving the page is safe: Today shows the open draft; coming back with `?setup=<id>` or with no query (the open draft) restores it. A failure shows one reason and **Try again** or **Paste instead**.
3. **Check**: values grouped by page: You, Answers, Lowest pay, Searches, Writing style, Resume studio, Your account. Each row has a keep checkbox, a source chip (From your resume, You said, Suggested, Recommended), and a **Where this came from** disclosure with the resume line. Needs-you rows show an empty input marked **Only you can answer this**. **Lowest pay** sets the profile pay floor, the salary answer, and each kept search minimum from one amount, currency, and period. **Edit** on a search opens a sheet for names, titles, must and nice skills, place, work mode, how much we do, and when we search. **See every detail** lists every fact with its quote. Edits, search overrides, and keep choices autosave after 700 ms. **Save for later** keeps the draft and returns to Today.
4. **AI**: when AI is off, the page offers the AI settings and a continue action. Adding AI and reading again keeps the choices already made.
5. **Done**: after apply, the page goes to the first new search with a one-time **We filled your pages** panel. Without a search it goes to the profile. Today shows **Setup done** with **Undo setup** for 7 days.

## Save paths

| Action | API | Effect |
| --- | --- | --- |
| Choose a file | `POST /profiles/{id}/documents` | Uploads and extracts text locally |
| Read my resume | `POST /onboarding/setups` | Creates the draft (`document_id` or `text`), runs inline in dev, queued in the background |
| Poll | `GET /onboarding/setups/{id}` | Status, steps, bundle |
| Restore | `GET /onboarding/setups` | The open draft for the default profile |
| Keep, edit, skip | `PATCH /onboarding/setups/{id}/decisions` | Autosaved review state, lowest pay, and per-search overrides |
| Use these | `POST .../validate` then `POST .../apply` with `Idempotency-Key` | One transaction through the profile, answer, track, schedule, voice, resume, and account services |
| Try again | `POST .../retry` | Resumes at the first unfinished step; `{with_ai:true}` upgrades a rules draft |
| Cancel | `POST .../cancel` | Stops a queued or running draft |

## Validation and edge cases

- Fewer than 200 pasted characters: the page asks for more text before starting.
- Unreadable or scanned file: the API returns `setup_document_unreadable` (or `needs_ocr`); the page says to paste or use a Word file.
- No AI key: the draft finishes with basics, links, skills, a search, a schedule, answers, and writing style. The notice says so.
- Another draft is open: `409 setup_open_exists`; the open draft loads instead.
- Daily setup cap: `429 setup_limit_reached`.
- Some values changed elsewhere before apply: `409 setup_stale`; the page refreshes and asks the user to check the marked rows.
- Double click or a retried request: the same `Idempotency-Key` returns the same result; a different key is rejected.
- Apply failure: the whole transaction rolls back and the draft stays ready.
- Viewer role: the API refuses with 403; the page shows the error.
- Search edits are re-validated on apply: must-have skills stay a subset of the person's skills, and languages, education, and clearance stay empty.
- Lowest pay cleared: nothing is written to the profile floor, salary answer, or searches.
- The full history editor is not on this screen. Facts are reviewed in summary form, edited in Profile after saving.
- After apply, the marker line on Profile, Answers, Writing style, What to look for, and Studio says where the content came from and points at that page's AI control. **Got it** hides it for this user.

## Entry points

| Entry | Path |
| --- | --- |
| Registration | Lands on `/start` |
| Profile menu and Today checklist | `/start` |
| Settings > General | **Set up from a resume** card |
| Create workspace dialog | Optional resume step after the name |
| Profile > Files merge | **Review changes** after a merge |
| People I help | **Start from their resume** |

## Implementation map

`apps/web/app/pages/start.vue` · `apps/web/app/lib/setup.ts` (review helpers, tested in `apps/web/tests/setup.test.ts`) · API `apps/api/app/onboarding/` · docs [`architecture/setup.md`](../../../architecture/setup.md).

## Agent parity

Starting and applying stay in the web UI. Phase 12b adds a read-only `get_setup_draft` tool.
