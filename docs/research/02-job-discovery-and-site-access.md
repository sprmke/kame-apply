# Research 02: Job discovery, global coverage, and site access

**Researched:** 2026-10-28 · Feeds into Phases 4, 5, 12, 16.

The question asked was how to crawl the internet for open roles, including sites that need a login (LinkedIn, JobStreet, Indeed), and how to get past bot checks. Short answer: **most of the world's jobs are published through a small number of company ATS platforms with public JSON endpoints.** Covering those, plus official board APIs, email alerts, and a browser extension in the user's own session, gets more jobs, with better data, than scraping gated boards. It also doesn't get the user's accounts banned. Section 5 explains why we don't build bot evasion.

## 1. Coverage strategy (layers, cheapest and safest first)

```
Layer 1  Company ATS APIs ─────────── largest share of direct-employer jobs; full JD, structured fields; zero auth
Layer 2  Job-board / aggregator APIs ─ broad + country coverage via official free keys
Layer 3  Company career pages ─────── schema.org JobPosting JSON-LD + sitemaps (what Google for Jobs reads)
Layer 4  Email job alerts ─────────── LinkedIn / JobStreet / Indeed / Glassdoor alerts forwarded to the workspace inbox
Layer 5  Browser-extension clips ──── user saves any job page they are viewing (incl. logged-in sites)
Layer 6  Personal-mode adapters ───── logged-out public search pages (LinkedIn guest, JobStreet public), opt-in, low volume
```

Every job keeps links to **all** places it was seen; the canonical apply URL prefers the company ATS (better for the user, no platform ToS issues for assisted applying).

## 2. Source catalog

### Layer 1: ATS platforms (public endpoints, per company "board")

| ATS | Public endpoint (per company slug) | Notes |
| --- | --- | --- |
| Greenhouse | `GET boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` | Proven in kame-hunt. Questions per job: `/jobs/{id}?questions=true` (useful for pre-drafting answers). |
| Lever | `GET api.lever.co/v0/postings/{slug}?mode=json` (EU: `api.eu.lever.co`) | `workplaceType`, `country`. Proven in kame-hunt. |
| Ashby | `GET api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true` | Many AI startups; structured compensation. Proven. |
| Workable | `GET apply.workable.com/api/v1/widget/accounts/{slug}` | Proven. |
| SmartRecruiters | `GET api.smartrecruiters.com/v1/companies/{id}/postings` | Official public Posting API. |
| Recruitee | `GET {slug}.recruitee.com/api/offers/` | Public careers API. |
| Personio | `GET {slug}.jobs.personio.de/xml` (also `.com`) | XML feed, strong in EU. |
| Workday | `POST {tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs` | JSON endpoint behind Workday's public career sites. Not an official API: parse defensively, keep low volume, back off on errors. Huge enterprise coverage. |
| BambooHR | `GET {slug}.bamboohr.com/careers/list` | JSON list, verify per tenant. |
| Breezy HR | `GET {slug}.breezy.hr/json` | Verify per tenant. |
| Teamtailor, JazzHR, Rippling, Pinpoint, Dover, Gem, Jobvite, iCIMS, Taleo, SuccessFactors | Career pages | Use Layer 3 (JSON-LD/sitemap) via a generic adapter; add dedicated adapters only when volume justifies it. |

#### The company directory (how coverage grows by itself)

ATS endpoints need company slugs. We build and maintain a `company_boards` directory automatically:

1. **Common Crawl index** (free, public): query the CDX index for URL patterns like `job-boards.greenhouse.io/*`, `boards.greenhouse.io/*`, `jobs.lever.co/*`, `jobs.ashbyhq.com/*`, `apply.workable.com/*`, `*.myworkdayjobs.com/*`, `jobs.smartrecruiters.com/*`, `*.recruitee.com/*`, `*.jobs.personio.*`. Extract slugs, then validate each one against its API. This alone yields tens of thousands of boards. Refresh monthly per new crawl.
2. **Link mining:** every job we ingest from boards, emails, or clips whose apply URL points to an ATS adds that board to the directory.
3. **User adds:** paste a careers URL; we detect the ATS and slug.
4. **Health checks:** boards that 404 or stay empty for 60 days are deactivated (kame-hunt `companies:check`, automated).
5. **Smart polling:** boards are polled by tier. Boards that matched any Track recently get frequent polls; cold boards get weekly polls. Use `ETag`/`If-Modified-Since` where supported.

Directory data (company name, domain, ATS, slug, size/industry when known) is **global** (shared across tenants), so every new workspace benefits immediately.

### Layer 2: Job-board and aggregator APIs

| Source | Access | Coverage | Notes |
| --- | --- | --- | --- |
| Adzuna API | Free developer key | ~20 countries (US, UK, AU, CA, DE, FR, IN, NZ, SG, ZA, BR, NL, PL, ...) | Salary data and histograms (also good for salary insights). |
| Jooble API | Free key on request | ~70 countries incl. PH | Aggregator; dedupe heavily. |
| Careerjet API | Free affiliate key | ~90 countries incl. PH | Aggregator; requires user IP/agent params per their terms. |
| USAJobs | Free key | US federal | |
| Reed (UK) | Free key | UK | |
| The Muse | Public API | US-heavy | |
| Remotive, Remote OK, Himalayas, Arbeitnow, Jobicy, We Work Remotely (RSS), Working Nomads | Public JSON/RSS | Remote | Proven in kame-hunt (most); attribution and no-republish terms respected. |
| HN "Who is hiring" | Algolia HN API | Startups | Monthly thread parsing (LLM-assisted extraction). |
| Regional boards with RSS/APIs | Varies | Per country | Added through the source-adapter skill as demand appears. |

Not available as free APIs: LinkedIn, Indeed (publisher API closed), Glassdoor, JobStreet/SEEK (partner-only), ZipRecruiter (partner). These are covered by Layers 4–6.

### Layer 3: Company career pages (generic adapter)

- Read `sitemap.xml` + careers pages; extract `application/ld+json` objects of `@type: JobPosting` (title, description, datePosted, validThrough, employmentType, hiringOrganization, jobLocation, applicantLocationRequirements, jobLocationType=TELECOMMUTE, baseSalary). This is the same data Google for Jobs indexes, published by employers so that crawlers read it.
- Respect `robots.txt` and crawl-delay; descriptive User-Agent with contact URL; cache; conditional requests.
- Tooling: `httpx` + `selectolax` for static pages; `extruct` for JSON-LD; Playwright only for JS-only pages, rate limited; optional Crawl4AI for markdown extraction of non-structured pages, with an LLM to extract fields.

### Layer 4: Email job alerts (covers gated platforms without scraping)

- Each workspace gets a private inbound address (e.g. `alerts+{token}@in.kameapply.app`) via **Cloudflare Email Routing → Email Worker → API webhook** (free).
- The user sets up saved searches on LinkedIn/JobStreet/Indeed/Glassdoor/Kalibrr and forwards or auto-forwards the alert emails. Parsers per sender (template-based, LLM fallback) turn them into jobs, then follow links to the employer ATS when present.
- Why not Gmail API by default: reading Gmail is a restricted OAuth scope. A public multi-tenant app then needs Google's verification plus a paid annual security assessment. Forwarding avoids that cost entirely. Gmail OAuth stays optional for personal/self-hosted mode (reuse kame-homes `gmail-listener`).

### Layer 5: Browser extension clips

When the user is on any job page (LinkedIn, JobStreet, Indeed, a company site), the extension's **Save to Track** reads the page the user is viewing and sends it to the app. It also detects when the user has applied (submit button clicked / confirmation page) and logs the application. This is the Teal/Huntr/Simplify pattern. It's user-initiated, at human pace, in the user's own session; no background crawling of logged-in pages.

### Layer 6: Personal-mode adapters (opt-in, off by default)

Logged-out public search endpoints (LinkedIn `jobs-guest` search, JobStreet public search, optionally `python-jobspy`) as used by kame-hunt and AI Job Search.

Guardrails: workspace owner must opt in and acknowledge the site's terms; max frequency every 4 hours; small page caps; never logged in; **automatic disable on any block signal** (HTTP 429/999, auth wall, challenge page), with no retry through evasion. In hosted multi-tenant mode these run with global caps shared across all tenants. If the platform objects, we turn them off.

## 3. Normalization and dedupe

- Canonical schema (`jobs`): source ids, canonical URL, apply URL(s), company (resolved to `companies`), title, normalized title, occupation codes (ESCO/O*NET via classifier), seniority, employment type, work mode, locations (geocoded), remote eligibility (countries/regions/timezones, parsed from text with an LLM when not structured), salary (min/max/currency/period, normalized to USD/month for filtering), skills (extracted + mapped to ESCO skills), description (sanitized HTML + text), posted/expiry dates, language, content hash.
- **Dedupe:** exact (ATS id), then fuzzy: company + normalized title + location + description MinHash/SimHash. Duplicates merge into one job with multiple `job_sources` rows.
- **Repost detection:** same content hash reappearing with a new id → keep history (useful scam/ghost-job signal).
- **Expiry:** re-check apply URL / ATS listing; mark `closed` when gone.

## 4. "Every job on the planet": what that honestly means

- **Role coverage is unlimited.** Tracks accept any occupation: free text + ESCO (multilingual) + O*NET codes, so nurses, welders, chefs, lawyers, and engineers are all first-class. Criteria fields are role-agnostic.
- **Geographic coverage depends on sources.** We keep a `country_source_registry` showing, per country, which sources cover it and how well. The UI tells the user plainly when their country is thinly covered and suggests Layer 4/5 (alerts + clipper) for local boards. New regional adapters follow the `source-adapter` skill.

## 5. The bypass question

The request was for deep research into making sites believe we are a real human: bypassing security checks, stealth browsers, CAPTCHA solving. **Kame Apply will not build or plan that.** This is the same rule `kame-hunt` already follows (its `CLAUDE.md` rule 3).

What we will not do: fingerprint spoofing / stealth plugins, CAPTCHA-solving services (e.g. CapSolver, which ApplyPilot integrates), residential-proxy rotation, synthetic "human-like" mouse/typing patterns meant to fool detectors, or scraping logged-in pages of platforms whose terms forbid it.

Why, beyond the ethics:

1. **It burns the user's most valuable asset.** LinkedIn/Indeed/JobStreet restrict or ban accounts tied to automation. AIHawk's history shows this. A user's LinkedIn is worth more than any number of bot applications.
2. **It's an arms race that breaks weekly.** Detection vendors (Cloudflare, DataDome, Akamai, hCaptcha) update constantly; a product built on evasion is permanently broken.
3. **It costs money** (proxies, solvers), which conflicts with the free-to-run goal.
4. **Legal exposure** for a multi-tenant service accessing sites against their terms on behalf of many users.
5. **It isn't needed.** The layers above reach most direct-employer jobs, and the extension + live takeover handle the rest *with a real human present*, so there's nothing to bypass.

What we do instead when a site challenges us: the run pauses, the user gets a "Needs you" notification, solves it themselves in the live view or their own browser, and the run resumes from saved progress.

## 6. Politeness and compliance checklist (every adapter)

- [ ] Official API or public endpoint; terms reviewed and recorded in the adapter's docstring.
- [ ] Descriptive `User-Agent` with contact URL; no browser impersonation.
- [ ] Per-host rate limit and concurrency cap (DBOS queue limits); exponential backoff; circuit breaker on repeated errors.
- [ ] Conditional requests / caching; poll frequency proportional to value.
- [ ] `robots.txt` respected for HTML crawling.
- [ ] Attribution + link back to original posting; no republishing outside the workspace.
- [ ] Block signal ⇒ disable + alert, never evade.
