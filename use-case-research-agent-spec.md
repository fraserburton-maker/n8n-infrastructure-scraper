# Use Case Research Agent — Project Specification

## Project Summary

A Next.js web application hosted on Vercel that researches GIS/geospatial use cases for specific industry verticals. It scrapes approved websites, extracts a capability list, deep-searches each capability individually, scrapes full page content, scores confidence, deduplicates, cross-references against existing research vaults, and pushes structured markdown notes to a GitHub repository.

---

## Key Decisions (Already Made)

| Decision | Choice |
|---|---|
| Hosting | Vercel |
| Framework | Next.js 14 (App Router) |
| Storage | GitHub (user's own account) — markdown files |
| AI | Claude API (claude-sonnet-4-6) |
| Scraping | Firecrawl API |
| Auth | GitHub OAuth (single user initially) |
| Notifications | Email (Resend API) |
| Obsidian | Optional — user can sync via Obsidian Git plugin |
| Reruns | Append only — never overwrite existing notes |
| Capabilities | Shared library across industries |
| Testing | 5 capabilities max (configurable via env var) |

---

## Tech Stack

```
Frontend:       Next.js 14 (App Router) + TypeScript
Styling:        Tailwind CSS + shadcn/ui
AI:             Anthropic SDK (claude-sonnet-4-6)
Scraping:       Firecrawl SDK
GitHub:         Octokit REST SDK
Email:          Resend SDK
Streaming:      Server-Sent Events (SSE) via Next.js Route Handlers
State:          Zustand (client), Redis (Upstash) for job state
```

---

## Environment Variables

```env
# Claude
ANTHROPIC_API_KEY=

# Firecrawl
FIRECRAWL_API_KEY=

# GitHub OAuth App
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_CALLBACK_URL=

# GitHub target repo (user's research repo)
GITHUB_REPO_OWNER=
GITHUB_REPO_NAME=use-case-research

# Email
RESEND_API_KEY=
NOTIFICATION_EMAIL=

# App
NEXTAUTH_SECRET=
NEXTAUTH_URL=
TEST_MODE=true          # limits to 5 capabilities when true
MAX_CAPABILITIES=5      # used when TEST_MODE=true
```

---

## GitHub Repo Structure (Target Output)

```
use-case-research/                        ← user's GitHub repo
├── _capability-library/
│   ├── 00-Library-Index.md               ← master list of all known capabilities
│   └── capabilities/
│       ├── digital-twin.md               ← reusable across industries
│       ├── asset-management-gis.md
│       └── ...
├── Local Councils/
│   ├── 00-Master-Index.md
│   ├── Use Cases/
│   │   ├── brisbane-digital-twin-roads.md
│   │   └── ...
│   └── Cross References/
│       └── Links to Capability Library.md
├── State Government/
│   ├── 00-Master-Index.md
│   └── Use Cases/
├── Federal Government/
├── Resources/
└── Esri Capabilities/                    ← existing vault (import on setup)
    └── Capabilities/
        ├── 00-Master-Index.md
        └── *.md                          ← 44 existing notes
```

---

## Note Frontmatter Schema

### Use Case Note
```markdown
---
id: brisbane-digital-twin-roads
title: City of Brisbane — Digital Twin for Roads Asset Management
industry: Local Councils
sub_vertical: Roads & Infrastructure
organisation: City of Brisbane
geography: Australia / QLD
technology:
  - ArcGIS
  - Digital Twin
  - Asset Management
confidence: 87
source: https://...
scraped: 2026-03-22
run_id: run_abc123
related:
  - "../../_capability-library/capabilities/digital-twin.md"
  - "../../Esri Capabilities/Capabilities/digital-twin-water-utilities.md"
tags:
  - local-council
  - digital-twin
  - roads
  - australia
---

# City of Brisbane — Digital Twin for Roads Asset Management

## Overview
[full content — no summaries]

## Problem / Challenge
[full content]

## Solution
[full content]

## Outcomes & Business Value
[full content]

## Technical Detail
[full content]

## Source Content
[full scraped markdown — untruncated]
```

### Capability Library Note
```markdown
---
id: digital-twin
title: Digital Twin
description: Real-time virtual representation of physical assets for monitoring, simulation and decision-making
industries:
  - Local Councils
  - State Government
  - Utilities
  - Resources
technology_tags:
  - ArcGIS
  - IoT
  - BIM
  - Sensors
related_use_cases: []        ← populated automatically on each run
created: 2026-03-22
updated: 2026-03-22
---
```

---

## Application Pages

```
/                         Landing — connect GitHub, setup APIs
/setup                    First-run wizard (GitHub OAuth, repo selection/creation)
/dashboard                Run history, vault stats, rerun buttons
/research/new             New research wizard (multi-step)
/research/[runId]         Live progress view (SSE streaming)
/research/[runId]/review  Results review — confidence scores, duplicates
/capabilities             Capability library browser
/settings                 API keys, email, GitHub config
```

---

## Research Wizard — 6 Steps

### Step 1: Industry & Scope
- Industry: Local Councils | State Government | Federal Government | Resources | Other
- Geography: Australia | Global | Specific region (free text)
- Creates a `runId` (uuid) on submission

### Step 2: Technology Focus *(optional)*
- Checkboxes: ArcGIS/Esri, Digital Twin, Asset Management, Field Mobility, Spatial Analytics, IoT/Sensors, Planning & Approvals, Emergency Management
- Or: leave blank for broad search

### Step 3: Source Selection
- Radio: "Find sites for me" | "I have a list"
- If list: textarea for URLs (one per line)
- Depth: Full detail (always — no summaries)

### Step 4: Site Validation *(if "find sites" selected)*
- Agent runs 5–8 Firecrawl searches
- Returns ranked list of sites with:
  - URL
  - Description of what it covers
  - Confidence score (0–100)
  - Recommended: Yes / Maybe / No
- User can approve/reject each, add custom URLs
- Min 1 site required to proceed

### Step 5: Capability Review
- Agent scrapes approved sites in full
- Claude extracts structured capability list
- Deduplicates against `_capability-library/` (existing capabilities shown with "already known" badge)
- New capabilities shown with checkbox (default: checked)
- Low confidence (<50%) shown unchecked with reason
- User can add manual capabilities
- TEST_MODE: caps at MAX_CAPABILITIES (default 5)

### Step 6: Confirm & Launch
- Summary: X sites → Y capabilities → estimated Z searches + scrapes
- Estimated time shown
- Email field (pre-filled from settings)
- [Start Research] button → redirects to /research/[runId]

---

## Research Pipeline (Server-Side)

Runs as a Next.js Route Handler using SSE to stream progress to the client.

```
POST /api/research/[runId]/start
GET  /api/research/[runId]/stream   ← SSE endpoint
```

### Pipeline Steps

```
1. SITE SCRAPE
   For each approved site:
   - firecrawl.map(url) → get all sub-pages
   - Filter to relevant paths (case-studies, industries, spotlight, etc.)
   - firecrawl.scrape(url, { onlyMainContent: false }) → full content
   - Stream event: { step: 'site_scrape', site, pagesFound, status }

2. CAPABILITY EXTRACTION
   - Claude prompt: extract structured capability list from scraped content
   - Output: [{ name, description, technology_tags, confidence }]
   - Deduplicate against capability library (fuzzy name match + Claude similarity)
   - Stream event: { step: 'capabilities_extracted', count, newCount, existing }

3. DEEP SEARCH (per capability, parallelised in batches of 3)
   For each approved capability:
   - Build search query: "{capability} {industry} {geography} site:esri.com OR site:esriaustralia.com.au OR ..."
   - firecrawl.search(query, { limit: 5 })
   - Claude selects best URL from results
   - Stream event: { step: 'search', capability, urlFound }

4. FULL SCRAPE (per capability)
   - firecrawl.scrape(bestUrl, { onlyMainContent: false })
   - Full content — no truncation
   - Stream event: { step: 'scrape', capability, contentLength }

5. CONFIDENCE SCORING (per note)
   Claude evaluates against 5 criteria:
   - Named organisation (+20)
   - Specific technology named (+20)
   - Measurable outcome stated (+25)
   - Relevant to industry + geography (+20)
   - Content depth / not a snippet (+15)
   Score: 0–100
   Stream event: { step: 'scored', capability, score }

6. DEDUPLICATION
   - Compare each new note against existing notes in same industry folder
   - Claude similarity check on: organisation + capability + technology
   - If duplicate: merge sources, keep highest confidence score
   - Stream event: { step: 'dedup', merged, kept }

7. CROSS-VAULT REFERENCING
   - Compare each note against:
     a. _capability-library/ (always)
     b. Esri Capabilities/ (always)
     c. Other industry folders (if capability is generic)
   - Claude semantic similarity → add related: links to frontmatter
   - Stream event: { step: 'crossref', capability, refsFound }

8. GITHUB PUSH
   - Append mode: check if file exists → skip if exists, write if new
   - Update 00-Master-Index.md (append new rows, don't rewrite existing)
   - Update _capability-library/ with any new capabilities
   - Single commit per run: "Research run: {industry} — {date} ({count} new cases)"
   - Stream event: { step: 'github_push', filesWritten, filesSkipped }

9. EMAIL NOTIFICATION
   Resend email with:
   - Run summary (industry, geography, duration)
   - Stats: X use cases added, Y duplicates skipped, Z cross-references found
   - Link to GitHub folder
   - List of notes written (with confidence scores)
   - Stream event: { step: 'complete', summary }
```

---

## Rerun Behaviour

- Dashboard shows each past run with a [Rerun] button
- Rerun re-uses same: industry, geography, tech focus, approved sites
- Opens wizard at Step 5 (Capability Review) — pre-populated with previous capability list
- User can add/remove capabilities before launching
- Pipeline runs in append mode:
  - Existing notes → skipped (logged as "already exists")
  - New notes → written
  - Master index → new rows appended, existing rows untouched
- New `runId` generated, new commit

---

## Capability Library Behaviour

- `_capability-library/` is shared across all industries
- When a capability is first discovered in any industry run, it's added to the library
- Subsequent runs in other industries check library first → "already known" badge
- Library notes accumulate `related_use_cases` links over time
- Library index (`00-Library-Index.md`) is a table of all known capabilities with which industries they've been found in

---

## Confidence Score UI

| Score | Label | Colour | Default included |
|---|---|---|---|
| 75–100 | High confidence | Green | Yes |
| 50–74 | Medium confidence | Amber | Yes (with warning) |
| <50 | Low confidence | Red | No (user must manually include) |

---

## Email Notification Template (Resend)

```
Subject: Research Complete — {Industry} ({N} new use cases)

Run completed in {duration}

Industry:    {industry}
Geography:   {geography}
Sites used:  {n}
Capabilities researched: {n}

Results:
  ✅ {n} new use cases added
  ⏭️  {n} duplicates skipped (already existed)
  🔗 {n} cross-references found
  ⚠️  {n} low confidence (excluded)

View on GitHub: https://github.com/{owner}/{repo}/tree/main/{industry}/

Notes added:
  - {title} (confidence: {score}%)
  - ...

---
Use Case Research Agent
```

---

## Build Order (Recommended)

### Phase 1 — Foundation
1. `npx create-next-app@latest use-case-research --typescript --tailwind --app`
2. Install deps: `@anthropic-ai/sdk firecrawl-js @octokit/rest resend next-auth zustand`
3. Install shadcn/ui components: button, card, checkbox, progress, badge, input, textarea, select
4. Set up `.env.local` with all keys
5. GitHub OAuth app setup (github.com/settings/developers)
6. Resend account + verified domain/email

### Phase 2 — GitHub Integration
7. `lib/github.ts` — Octokit wrapper: readFile, writeFile, appendToIndex, listFolder, commitBatch
8. `lib/github-vault.ts` — vault-aware helpers: noteExists, appendNote, updateMasterIndex
9. Test: write a single markdown note to repo

### Phase 3 — Core Pipeline
10. `lib/firecrawl.ts` — search, scrape, map wrappers
11. `lib/claude.ts` — extractCapabilities, scoreConfidence, findCrossRefs, selectBestUrl, detectDuplicate
12. `lib/pipeline.ts` — full orchestration (steps 1–9 above)
13. `app/api/research/[runId]/stream/route.ts` — SSE route handler
14. Test pipeline end-to-end with TEST_MODE=true (5 capabilities)

### Phase 4 — UI
15. `/research/new` — 6-step wizard
16. `/research/[runId]` — live progress with SSE
17. `/research/[runId]/review` — results review
18. `/dashboard` — run history + rerun buttons
19. `/capabilities` — capability library browser
20. `/settings` — API keys, email, GitHub config

### Phase 5 — Polish & Deploy
21. Error handling + retry logic for Firecrawl timeouts
22. Rate limiting (Firecrawl: 10 req/min on free tier)
23. Vercel deployment + env vars
24. End-to-end test with a real industry (Local Councils, Australia, 5 capabilities)

---

## Claude Prompts (Key Ones)

### Extract Capabilities from Scraped Content
```
You are analyzing scraped website content from {sites} to extract a structured list of GIS/geospatial capabilities for the {industry} industry.

For each distinct capability you find, return a JSON array:
[{
  "name": "string — short capability name",
  "description": "string — what this capability does",
  "technology_tags": ["string"],
  "sub_vertical": "string — e.g. Roads, Water, Planning",
  "confidence": 0-100,
  "confidence_reason": "string"
}]

Rules:
- Only include capabilities with real evidence in the content
- Prefer specific over generic (e.g. "GIS-enabled Planning Approvals" over "GIS")
- If confidence <50, include it but note why
- Deduplicate within your response

Content:
{scrapedContent}
```

### Score Confidence
```
Score this use case note on a scale of 0–100 based on these criteria:
- Named organisation (not generic): 0 or 20
- Specific technology/product named: 0 or 20
- Measurable outcome or business value: 0 or 25
- Relevant to {industry} in {geography}: 0 or 20
- Content depth (not a marketing snippet): 0–15

Return JSON: { "score": 0-100, "breakdown": { criterion: score }, "flags": ["any issues"] }

Note content:
{noteContent}
```

### Find Cross References
```
Compare this use case against the following existing notes and identify semantic matches.
Return JSON array of matches with similarity score (0–100) and reason.
Only include matches with score >60.

New use case:
{newNote}

Existing notes to compare against:
{existingNotes}

Return: [{ "file": "path/to/note.md", "similarity": 0-100, "reason": "string" }]
```

### Select Best URL from Search Results
```
Given these search results for the capability "{capability}" in the {industry} industry ({geography}),
select the single best URL to scrape for a detailed use case.

Prefer in this order: esriaustralia.com.au, esri.com, udcus.com, ngis.com.au, vendor case study pages.
Avoid: generic aggregators, news articles without detail, paywalled content.

Return JSON: { "url": "string", "reason": "string", "confidence": 0-100 }

Search results:
{searchResults}
```

---

## Testing Checklist

- [ ] GitHub OAuth login works
- [ ] Can create/read/write files to target GitHub repo
- [ ] Firecrawl search returns results
- [ ] Firecrawl scrape returns full content
- [ ] Claude extracts capability list from scraped content
- [ ] TEST_MODE limits to 5 capabilities
- [ ] SSE streaming shows progress in UI
- [ ] Notes written to correct GitHub folder
- [ ] Duplicate detection works (run twice, second run skips existing)
- [ ] Cross-references added to frontmatter
- [ ] Master index updated (append only)
- [ ] Rerun button works from dashboard
- [ ] Email notification received on completion
- [ ] Vercel deployment works with env vars

---

## Reference — Existing Esri Capabilities Vault

The 44 existing capability notes live in Obsidian (local). To import into the GitHub repo:
- Copy all `.md` files from the `Capabilities/` folder in Obsidian vault
- Push to `use-case-research/Esri Capabilities/Capabilities/` in the GitHub repo
- The app will reference these automatically during cross-vault matching

Existing vault sources: udcus.com, esri.com, esriaustralia.com.au, sspinnovations.com
Industries covered: Utilities (primary), AEC, Rail, Ports, Airports

---

*Specification version: 1.0 — 2026-03-22*
*Ready to build. Start with Phase 1 (Foundation) and work through phases in order.*
*Set TEST_MODE=true in .env.local to cap all runs at 5 capabilities during development.*
