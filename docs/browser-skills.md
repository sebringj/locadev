# Browser-first workflow — the proven pattern

What worked in **multiple orgs** (and what locadev is built around):

```text
  chrome-debug-profile  +  playwright
            │
            ▼
   signed-in Chrome (your session: SSO, cookies, apps)
            │
            ▼
   site / product skills layered on top
   (Jira UI, ADO boards, Slack/Teams chat, Confluence, PDFs…)
            │
            ▼
   snapshots + citations  →  /grounding  →  code + local cloud
```

**Primary path = drive the real product UIs in the user’s browser.**  
You already have access to Jira, Azure DevOps, Slack, Teams, SharePoint, chat attachments, etc.  
**You do not need API keys for every service** when the agent can click and read what you already see.

API CLIs (`./boards/board.sh`, tokens, PATs) are **optional accelerators** — not the main integration story.

---

## Why browser-first wins

| Reality | Browser path | API-key path |
|---------|--------------|--------------|
| You’re already logged into Jira / ADO / Slack | Use that session via CDP | Mint tokens, scopes, rotate secrets |
| Spec lives in a **chat PDF** or **Excel** attached in Teams | Open the thread, open the file, snapshot | Often no API, or different product |
| Requirements are half in Confluence, half in a ticket comment | Navigate + capture both | Multiple APIs, incomplete fields |
| Org blocks “bot” API apps | Human session still works | Stuck |
| New SaaS every quarter | New thin **site skill** on the same CDP base | New OAuth app each time |

Requirements gathering is **not only structured tickets**. Typical successful captures:

- Jira / ADO work item **screens** (description, AC, comments, attachments)
- Slack / Teams / Discord **threads** (decisions, links, @mentions)
- **PDF / Excel / Word** opened from chat or SharePoint in Chrome
- Confluence / Notion / wiki pages
- Product admin UIs and vendor docs (signed-in)
- Email web UIs when that’s where the ask landed

Store evidence under **`.grok/local/requirements/`** (gitignored) and cite paths in **`/grounding`**.

---

## Foundation skills (stack these)

| Layer | Skill | Job |
|-------|--------|-----|
| **1 · Session** | **`/chrome-debug-profile`** | Work **copy** of the user’s Chrome profile + CDP (`:9222`). SSO, cookies, extensions as the user. |
| **2 · Automation** | **`/playwright`** (attach via `connectOverCDP`) | Drive pages, click, extract text, screenshot. Same skill family used for e2e — **session mode** for work, **clean Chromium** for CI e2e of *your* app. |
| **3 · Gather** | **`/web-requirements`** | AI plans first, then browse + synthesize requirements doc. Prefer CDP when anything is private. |
| **4 · Site skills** | `sites/*` / org-specific skills | Thin skills **on top of** chrome-debug + playwright: “open our Jira project”, “read Teams channel X”, “export this board view”. |
| **5 · Honesty** | **`/grounding`** | Pre-decision / post-ready citations from snapshots — not vibes. |

### Two uses of Playwright (don’t conflate)

| Mode | Browser | Purpose |
|------|---------|---------|
| **Session (default for workflow)** | Chrome via CDP (user profile work copy) | Boards, chat, PDFs, internal tools — **no API keys** |
| **CI / app e2e** | Clean Chromium | Prove **locadev consumer / your app** UI after you built it |

---

## Build skills on top (org pattern)

When a flow repeats (every sprint, every service):

1. Keep **chrome-debug-profile** + **playwright** as the base (never re-solve login).
2. Add `~/.grok/skills/sites/<slug>/SKILL.md` (or project `.grok/skills/…`) with:
   - entry URL(s), ready selector, click paths
   - what to snapshot for citations
   - safety (read-only vs allowed writes)
3. Invoke: load chrome-debug → ensure CDP → run site skill → cite → optional local cloud.

Examples of site skills:

- `jira-acme` — open issue, read AC, comment, transition **in the UI**
- `ado-boards` — open work item, board column, discussion
- `teams-spec` — open channel, open PDF/Excel preview, extract decisions
- `confluence-adr` — pull ADR pages for pre-decision citations

---

## Optional API path (boards CLI)

`./boards/board.sh` + `JIRA_API_TOKEN` / `AZURE_DEVOPS_EXT_PAT` is for when:

- headless automation without a display, or  
- the user prefers API over UI, or  
- CDP isn’t available

**Default recommendation for interactive AI workflow: browser UI first.**  
See `boards/README.md` — browser-first section is the lead; CLI is secondary.

---

## Full loop (corrected)

```text
  you type
      │
      ▼
  chrome-debug + playwright (signed-in)
      │
      ├── gather: web UIs, chat, PDF/Excel, tickets, wikis
      ├── clarify: post/read in real Slack/Teams (or local fakes for practice)
      └── update boards: click Jira/ADO in the browser (or board.sh if API)
      │
      ▼
  pre-decision (/grounding) ← snapshot paths + quotes
      │
      ▼
  implement + local cloud (make up / verify)
      │
      ▼
  post-ready ← tests, verify, board/PR evidence (UI screenshot or API)
      │
      ▼
  gh PR / say ready
```

### Citation examples

```bash
# Snapshots beat inventing "what the ticket said"
LOCADEV_CITATIONS='.grok/local/requirements/run-3/teams-pdf-page.md; .grok/local/requirements/run-3/jira-PROJ-12.md' \
LOCADEV_DECISION='Match AC in Jira; attachment PDF is source for field list' \
  ./hooks/pre-decision.sh
```

---

## Setup (signed-in base)

```bash
# Quit normal Chrome first (Cmd+Q)
chrome-profile-sync
chrome-debug
curl -s http://127.0.0.1:9222/json/version   # must succeed
```

Then attach Playwright with `chromium.connectOverCDP('http://127.0.0.1:9222')` — do **not** `launch()` a blank browser for board/chat work.

Local config (gitignored): `~/.grok/local/chrome-debug-profile.json`  
Template: skill `config.example.json`.

---

## Agent rules

1. **Prefer browser session** over inventing API integrations for SaaS the user already uses.  
2. **AI plan first** for gather; then browse.  
3. Requirements may live in **chat + attachments**, not only Jira fields — look there.  
4. Layer **site skills** on chrome-debug; don’t duplicate login in every skill.  
5. Cite **snapshot paths**; never invent ticket text.  
6. Read-only by default on signed-in CDP; only write (comment/transition) when the user asked.  
7. Clean Playwright e2e is for **your app** after implement — not a substitute for signed-in gather.

---

## Related

| Doc | Role |
|-----|------|
| [hooks/README.md](../hooks/README.md) | Pre/post grounding |
| [boards/README.md](../boards/README.md) | Browser-first boards + optional API CLI |
| [AGENTS.md](../AGENTS.md) | Agent loop |
| `/chrome-debug-profile` · `/playwright` · `/web-requirements` · `/grounding` | Slash skills |
