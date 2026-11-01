# Research 07: How recruiters and their AI tools find and screen candidates (2026)

**Researched:** 2026-10-28 · Feeds into Phases 6, 8, 9, 11, 13, 14 and the PRD's "Recruiter Lens" (F18) and "Be Found" (F19).

The ask: reverse-engineer how companies find and filter applicants today, both AI and human, and make sure every resume, answer, and application Kame Apply produces passes **both**.

> Evidence quality: vendor documentation (Workday HiredScore, Greenhouse) is strong. Most "ranking weight" claims about LinkedIn and ATS keyword scoring come from SEO/career blogs and are treated here as hypotheses, not facts. Our design never depends on an unverified weight. It does what holds under any plausible ranking model: clear evidence for each requirement in clean, parseable text.

## 1. The 2026 hiring funnel (where a candidate gets filtered)

```
 Sourcing (recruiter searches)         Inbound (candidate applies)
 LinkedIn Recruiter, ATS CRM             Company ATS: Workday, Greenhouse, Lever, Ashby,
 rediscovery, SeekOut/hireEZ/Gem          iCIMS, SuccessFactors, SmartRecruiters, Taleo
            │                                        │
            ▼                                        ▼
  (A) Search & match  ──────────►  (B) Parse resume → structured profile (Textkernel, Daxtra, in-house LLM parsers)
                                              │
                                   (C) Knockout / screening questions (work auth, location, years, salary, license)
                                              │
                                   (D) AI grading / matching (HiredScore A–D, Greenhouse Talent Matching,
                                       Lever AI Screening, Ashby, Eightfold, bolt-on screeners)
                                              │
                                   (E) Fraud / authenticity checks (identity, consistency, AI-content flags)
                                              │
                                   (F) Human skim (seconds per resume), then phone screen / AI interviewer
```

Why it matters: Greenhouse's March 2026 benchmark reported **applications per recruiter up ~412% from 2022 to 2025**. Humans can't read everything, so stages B–E decide who a human ever sees. Mass AI auto-apply caused that volume, which is why quality and fit, not volume, is the winning strategy.

## 2. Stage by stage: what the machine/human looks at, and what Kame Apply does

### (A) Sourcing: being found without applying

| How it works | Kame Apply response |
| --- | --- |
| Recruiters run keyword/boolean + AI-assisted semantic search in LinkedIn Recruiter and in their ATS's past-applicant database ("talent rediscovery"). Matching leans on **current title/headline, skills, location, recency of activity, and "open to work" (recruiters-only)** signals (blog consensus, unverified weights). | **F19 Be Found:** LinkedIn profile optimizer (headline, about, skills top-N, experience titles aligned with target Track titles, *truthful*); checklist to set "Open to work (recruiters only)" with target titles/locations; consistency check between resume and LinkedIn (dates, titles, companies). We generate text; the **user pastes it** (no LinkedIn automation). |
| Every application lands in the company's ATS and is searchable later for other roles. | Clean, well-structured resumes keep paying off: a strong parse makes the user findable in that company's ATS for future roles too. |

### (B) Parsing: the resume becomes fields

Parsers read text as a linear stream and map it into fields (contact, titles, employers, dates, education, skills). Common failures: multi-column layouts and tables (order scrambled), contact info in header/footer (lost), text in images or text boxes, icons as bullets, non-standard section headings, ambiguous dates, fancy fonts with broken text layers.

**HiredScore doesn't grade candidates without a resume or with unsupported formats** (Workday docs). Parsing failure is effectively rejection.

**Kame Apply:** single-column templates only; contact in body; standard headings (`Experience`, `Education`, `Skills`, `Projects`, `Certifications`); `Mon YYYY – Mon YYYY` dates; real text layer (Typst); no tables/graphics/icons; **parse round-trip test** on every generated resume: extract text with two independent parsers, re-parse to fields, and verify name/email/phone/each title/company/date survived in the right order. This is a hard gate in Phase 8.

### (C) Knockout questions

Binary filters before any scoring: work authorization / sponsorship, location or timezone, minimum years, degree/license, salary range, willingness to relocate, start date. Wrong answers are auto-rejects; untruthful answers are fraud.

**Kame Apply:** answer bank holds the truthful canonical answers (F1). Matching (Phase 6) **predicts knockouts from the posting** and marks jobs `not eligible` before the user wastes time. The apply engine never alters an eligibility answer to pass a filter.

### (D) AI grading and matching (the core of the "reverse engineering")

What the documented systems do:

- **Workday HiredScore:** grades A–D on how well the resume matches the job description's qualifications. The **August 2026 release adds an LLM evaluating each screenable qualification individually against the parsed resume**, with a Fit & Gap view for the recruiter.
- **Greenhouse Talent Matching:** assistive (not auto-reject), puts candidates in match categories **with reasoning**; candidates it can't analyze go to "Needs manual review"; candidates can opt out.
- **Lever AI Screening (VONQ):** ranked shortlist with reasoning visible to recruiters.
- **HireVue AI Interviewer, Paradox, and similar:** conversational/video screening that ranks before a recruiter call.

The common model in 2026 is **requirement → evidence matching**, not keyword density:

1. The system extracts the job's qualifications (must-have vs preferred), e.g. "5+ years React", "experience with AWS", "B2B SaaS", "led a team".
2. For each one, it looks for **evidence** in the parsed resume: the skill named in a role, with dates (years computed from role dates), with context (scope, outcome), and recency.
3. It aggregates into a grade/category and a human-readable fit/gap explanation.

What follows for optimization:

| Lever | Do (truthfully) | Don't |
| --- | --- | --- |
| **Terminology** | Use the posting's exact term **and** common variant/acronym where the user genuinely has it ("Amazon Web Services (AWS)", "CI/CD", "Kubernetes (K8s)"). | Paste the JD, hidden white text, keyword dumps. These are flagged and lose to evidence-based grading anyway. |
| **Evidence per requirement** | Put each must-have skill **inside an experience bullet** (with role dates) not only in a skills list, so years and recency compute. | Claim skills with no supporting role. |
| **Years math** | Make role dates exact and contiguous so computed years are right; mention total years in summary when it's a requirement. | Round up dates. |
| **Title alignment** | If the user's real title differs in naming but not substance, use "Official Title (equivalent: Target Title)" only when true, or reflect the target title in the summary line. | Change historical titles. |
| **Recency** | Order bullets so the most relevant evidence appears in the most recent roles first. | |
| **Must-haves first** | Summary + first bullets of the latest role cover the top 3–5 must-haves explicitly. | |
| **Gaps** | Missing must-have = real gap. Show it to the user; consider skipping the job or addressing adjacent experience honestly. | Insert it. |

**Kame Apply's "Recruiter Lens" (F18)** simulates this pipeline on our side before the user applies. It parses our own output, extracts the job's qualifications, runs a requirement-by-requirement evidence check with an LLM grader (HiredScore-style A–D with Fit & Gap), and shows what a recruiter's AI would likely conclude, plus a 7-second human-skim view (below). Tailoring (F7) then optimizes against that report, and the report is re-run after edits.

### (E) Fraud and authenticity checks

Survey data (Checkr 2026): 73% of companies have encountered AI-generated resumes/cover letters/assessments. Greenhouse 2026 (UK/IE/DE): 86% of recruiters caught or suspected candidate fraud in the past year. Screeners now check consistency (resume vs LinkedIn vs interview), identity, verifiable links, and generic AI-sounding text. Detection vendors themselves say AI-text detection is unreliable and favor interviews and work samples.

**Kame Apply:** truthful content is a competitive advantage here, not just an ethic. We add: consistency check (resume ↔ LinkedIn ↔ answers); verifiable links (GitHub/portfolio) surfaced; style-matched writing with banned stock phrases; specific facts over adjectives; and no mass-applying. A candidate who applies to 400 jobs at one company's ATS looks fraudulent, so we add a **per-company cap** and warn on many applications to the same employer.

### (F) The human skim

The widely cited eye-tracking study (Ladders, 2018) found ~7.4 seconds for the initial scan, focused on the top third: name, current title + company, previous title + company, dates, education. Many small companies still screen entirely by hand, sometimes from the email or PDF only.

**Kame Apply "skim view":** render the first page top third and highlight what a human sees in 7 seconds: current title vs target role, companies, dates, 3 strongest proof points. Rules: one-line summary that names the target role and top must-haves; bullets start with strong verbs and lead with outcome/metric; 1 page (<10 years experience) or 2 pages max; consistent formatting; no walls of text; PDF and DOCX available (some systems and humans prefer DOCX).

## 3. Other things that move interview odds (and how we use them)

| Factor | Evidence quality | Kame Apply |
| --- | --- | --- |
| **Apply early** (first 24–72 h of posting) | Strong practitioner consensus; recruiters review in order and close pipelines once full | Discovery frequency + "fresh" boost in ranking + notifications for strong new matches |
| **Referrals** | Consistently the highest-converting channel | P2: "who do I know there" prompts; outreach drafts the user sends (never auto-sent) |
| **Direct company ATS vs aggregator apply** | Aggregator "1-click" applies are often lower priority or lossy | Prefer canonical company ATS apply URL (research/02) |
| **Cover letters** | Mixed; read by humans at smaller companies, often ignored by large-company AI screeners | Optional per Track; short, specific, in user's voice; required only when the form asks |
| **Screening question quality** | Free-text answers are often read by humans at shortlisting | Answer Desk drafts grounded answers; user approves |
| **Salary expectations** | Out-of-band numbers knock out | Use posting range + Adzuna salary data to suggest a truthful range |
| **Follow-up** | Moderate | Reminder + draft follow-up after N days (user sends) |

## 4. Regulation that touches this (for awareness and product copy)

- **NYC Local Law 144** (in force since July 2023): employers using automated employment decision tools on NYC candidates must run bias audits and give notice; candidates can request an alternative process. We can surface this right in the UI for NYC postings (P2).
- **EU AI Act:** recruitment AI is "high-risk" (Annex III). Obligations fall on employers/vendors deploying screening tools. The application date is contested: 2 Aug 2026 vs. a reported Digital Omnibus delay to 2 Dec 2027. Kame Apply is a candidate-side tool and isn't a screening system, but its transparency matters: we tell users plainly what the AI did. Re-check before any EU launch.
- Platform terms (LinkedIn, Indeed, JobStreet) are covered in research/02.

## 5. Design implications summary (traced into phases)

1. **Recruiter Lens** report on every tailored resume (Phase 8, 9): parse round-trip, requirement-by-requirement Fit & Gap grade, human skim view, knockout prediction, authenticity/consistency checks.
2. **Per-job tailoring is MVP** (Phase 9): optimize against the Lens report under truthfulness rules, with diff + reasons, and re-grade.
3. **Matching mirrors screeners** (Phase 6): extract qualifications from each posting once and reuse for ranking, eligibility, tailoring, and answers.
4. **Templates are parse-safe by construction** (Phase 8).
5. **Be Found** (Phase 9 for LinkedIn text; P2 for more).
6. **Quality caps** (Phase 15): per-company and per-day caps; fresh-job priority.
