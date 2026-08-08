# Browser skills — meaning in the locadev AI workflow

Browser skills are **how the agent gathers and proves truth from the web** before inventing stack choices, board updates, or code. They are not optional fluff; they feed **citations** into pre-decision hooks and often **acceptance notes** on Jira/ADO.

```text
  /web-requirements  (+ /chrome-debug-profile if signed-in)
           │
           ▼
  snapshots under .grok/local/requirements/
           │
           ▼
  requirements doc + open questions
           │
     ┌─────┴──────┐
     ▼            ▼
  clarify in    pre-decision citations
  Slack/…       (paths, URLs, quotes)
     │            │
     └─────┬──────┘
           ▼
  boards (Jira / ADO) + local cloud + implement
           │
           ▼
  /playwright (e2e)  →  post-ready receipts
```

---

## Skill map (what each one *means*)

| Skill | Slash | Meaning | When | Output that counts as **citation** |
|-------|-------|---------|------|-------------------------------------|
| **web-requirements** | `/web-requirements` | **Gather** product/docs requirements from live pages — **AI plans first**, then Playwright browses | Start of a feature/integration; “what does this product actually do?” | `.grok/local/requirements/<run>/…` page snapshots + requirements md |
| **chrome-debug-profile** | `/chrome-debug-profile` | **Signed-in Chrome** via CDP (your cookies/SSO on a **work copy** of the profile) | Docs or admin UIs behind login | Same as above, but pages only visible when authenticated |
| **playwright** | `/playwright` | **E2E / UI proof** against an app (usually **clean** Chromium, CI-friendly) | After implement; smoke “does the UI work?” | test report, screenshots under `test-results/` → post-ready evidence |

### One-liners

- **web-requirements** = research the *product* (requirements).  
- **chrome-debug-profile** = *how* you open private pages (session).  
- **playwright** = *test* the app you built (verification).

Do **not** use `/playwright` as a substitute for requirements gathering.  
Do **not** use clean Chromium for tenant-only admin UIs — use CDP.

---

## Auth modes

| Mode | Skill stack | Browser |
|------|-------------|---------|
| Public docs / marketing | `web-requirements` only | Clean Chromium (`--clean`) |
| Logged-in product / internal docs | `chrome-debug-profile` **then** `web-requirements` | Chrome work profile + `connectOverCDP` (`http://127.0.0.1:9222`) |
| CI / app e2e | `playwright` | Clean Chromium (no personal profile) |

**CDP** = Chrome DevTools Protocol (remote debugging). Not CSP.

Setup (signed-in):

```bash
# Quit normal Chrome first
chrome-profile-sync    # copy profile → work dir
chrome-debug           # listen on :9222
curl -s http://127.0.0.1:9222/json/version
```

Local config (gitignored): `~/.grok/local/chrome-debug-profile.json`, `~/.grok/local/web-requirements.json`  
(or project `.grok/local/…`). Templates live in each skill’s `config.example.json`.

---

## Where this sits in the full loop

| Step | Browser skill role |
|------|--------------------|
| **1 · Gather** | `/web-requirements` produces the requirements doc + snapshots |
| **2 · Clarify** | Open questions from that doc go to Slack/Discord/Teams |
| **3 · Pre-decision** | Cite snapshot paths / URLs / quotes — not vibes |
| **4 · Boards** | Paste summary into `jira:…` / `ado:#…` comments; acceptance criteria from requirements |
| **5 · Local cloud + code** | Map integrations to locadev profiles (Azurite, fake channels, …) |
| **6 · Post-ready** | `/playwright` (or verify/tests) supplies UI receipts if the change is user-facing |

### Citation examples (hooks)

```bash
LOCADEV_CITATIONS='.grok/local/requirements/run-1/page-01/page.md; https://docs.example/api; jira:PROJ-12' \
LOCADEV_DECISION='Use Azurite for blob path per product docs' \
  ./hooks/pre-decision.sh

LOCADEV_EVIDENCE='verify:ok; playwright:e2e smoke passed; jira:PROJ-12 In Progress; gh:PR #8' \
LOCADEV_READY_CLAIM='Blob upload ready for review' \
  ./hooks/post-ready.sh
```

---

## Agent rules (browser)

1. **AI first** for requirements: plan URLs + questions **before** opening the browser.  
2. Prefer **read-only** navigation on signed-in CDP (full account power).  
3. Store captures under **`.grok/local/requirements/`** (never commit).  
4. **Do not invent** product facts that were not in snapshots, user text, or tickets.  
5. Map discovered cloud/integrations to **locadev** stand-ins when drafting the plan.  
6. After UI work, use **playwright** for proof — not another ad-hoc browse unless gathering more requirements.

---

## Related docs

| Doc | Role |
|-----|------|
| [hooks/README.md](../hooks/README.md) | Pre/post grounding gates |
| [boards/README.md](../boards/README.md) | Jira + ADO |
| [AGENTS.md](../AGENTS.md) | Full agent loop |
| `~/.grok/skills/web-requirements/SKILL.md` | Requirements skill detail |
| `~/.grok/skills/chrome-debug-profile/SKILL.md` | CDP / profile skill detail |
| `~/.grok/skills/playwright/SKILL.md` | E2E skill detail |
