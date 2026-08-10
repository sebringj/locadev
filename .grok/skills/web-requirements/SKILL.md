---
name: web-requirements
description: >
  AI-first requirements gathering from the web using Playwright: plan what to
  learn, then browse (clean Chromium or signed-in Chrome via CDP/chrome-debug-profile),
  snapshot pages, draft a requirements doc. Locadev: snapshots become pre-decision
  citations. Use for /web-requirements, "gather requirements", "read the product UI",
  "requirements from docs", signed-in discovery.
metadata:
  short-description: "AI + browser → requirements + citations"
user-invocable: true
---

# /web-requirements — gather (locadev)

**Means:** research requirements from **anywhere the browser can open** — not only marketing docs or Jira fields.

Include when relevant: product UIs, **Slack/Teams/Discord threads**, **PDF/Excel/Word** opened from chat or SharePoint, Confluence, ticket screens. Prefer **`/chrome-debug-profile` + CDP** so you don’t need SaaS API keys.

Output feeds **`/grounding` pre-decision**. Canonical long form: `~/.grok/skills/web-requirements/SKILL.md`.

## Phase 1 — AI first (no browser yet)

Produce: goal, auth need (public vs signed-in), ordered list of **URLs / channels / attachments**, questions to extract, success criteria. Ask where the truth lives if unclear (ticket vs chat PDF vs wiki).

## Phase 2 — Browser

| Mode | When | How |
|------|------|-----|
| **CDP signed-in** | Login / SSO / tenant UI | Load **`/chrome-debug-profile`** first; `chrome-profile-sync` → `chrome-debug`; CDP `http://127.0.0.1:9222` |
| **Clean** | Public docs | `chromium.launch` / snapshot helper `--clean` |

```bash
# Signed-in CDP up:
node ~/.grok/skills/web-requirements/scripts/attach-and-snapshot.mjs \
  --url 'https://…' --cdp http://127.0.0.1:9222 \
  --out ./.grok/local/requirements/run-1/page-01

# Public:
node ~/.grok/skills/web-requirements/scripts/attach-and-snapshot.mjs \
  --url 'https://…' --clean \
  --out ./.grok/local/requirements/run-1/page-01
```

Store under **`.grok/local/requirements/`** (gitignored). Do not commit.

## Phase 3 — Synthesize

- Requirements doc from `~/.grok/skills/web-requirements/references/requirements-doc-template.md`
- Open questions → channel (Slack/Discord/Teams)
- Integrations → locadev profiles (Azurite, fakes, …)
- **Citation list** for grounding:

```bash
LOCADEV_DECISION='…' \
LOCADEV_CITATIONS='.grok/local/requirements/run-1/page-01/page.md; https://…' \
  ./hooks/pre-decision.sh
```

## Not this skill

| Need | Skill |
|------|-------|
| Signed-in session only | `/chrome-debug-profile` |
| E2E after code | `/playwright` |
| Ready gate | `/grounding` |

See `docs/browser-skills.md`.
