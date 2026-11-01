# Phase 12: Answer Desk

**Status:** Done · **Release:** R1 · **Depends on:** 9 · **Features:** F9 · **Reference:** [`research/04`](../research/04-trust-safety-and-scam-detection.md) §5

## Goal

When a form can't be automated, the user answers its questions quickly with drafts grounded in their real facts and written in their voice. AI-restricted questions are respected.

## Acceptance scenarios

1. Paste a block with 6 questions → split into 6 items (with detected char limits like "max 500 characters") → drafts stream in; each has copy, counter, and tone controls (shorter / more specific / more casual / more formal).
2. A question with "Please answer without using AI tools" → no draft; shows "Write this yourself", with relevant profile facts as bullet notes and a text box.
3. Eligibility questions (authorization, sponsorship, salary, notice) are answered from the answer bank verbatim, labeled "from your answer bank".
4. "Save to answer bank" on an edited answer → reused next time a similar question appears (semantic match).
5. Answers attach to an application (if opened from one) and are listed in its detail.
6. Drafts contain no banned phrases and cite which profile facts they used (hover).

## Tasks

- [x] Question splitter (rules + LLM), constraint detection (limits, format: yes/no, number, date, select options if pasted).
- [x] AI-restriction detector (multilingual patterns + classifier) at question and page level; tested corpus.
- [x] Answer resolver: answer bank semantic match (embeddings) → profile facts retrieval → drafter with voice profile + banned phrases + verifier (no new facts) → length fit.
- [x] Truthful AI-use answers from a user-configured stance.
- [x] UI per blueprint §3.7 (keyboard: ⌘C copies the focused draft; Tab moves between items); mobile layout.
- [x] API reused by extension (Phase 13) and runner (Phase 15).

## Edge cases & failure modes

- Behavioral questions ("Tell us about a conflict") → STAR from profile; if no suitable story exists, ask the user for one (interview proposal), don't invent.
- Salary questions with ranges vs single number → follow the form's format; market data suggestion visible (Phase 18 improves).
- Questions in another language → answer in that language if the user allows, otherwise warn.
- Very short limits (e.g. 100 chars) → compress without losing the key fact.
- Legally sensitive questions (age, religion, marital status in some countries) → flag "employers usually shouldn't ask this"; user decides.

## Testing

Restriction detector corpus (≥ 80 phrasings, 6 languages) recall ≥ 98%; fabrication check on 30 Q&A; banned-phrase lint; E2E paste → copy.

## Docs to update

Route guide, `docs/architecture/answers.md` (new).

## Exit criteria

- [x] Scenarios 1–6 pass; evals green.
