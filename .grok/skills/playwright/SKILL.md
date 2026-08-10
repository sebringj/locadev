---
name: playwright
description: >
  Base Playwright e2e: scaffold, run, and fix browser UI tests. Clean Chromium,
  CI-friendly. In locadev: UI proof for post-ready receipts — not requirements
  gathering. Use for /playwright, e2e, "smoke the UI", "UI test", flaky tests.
metadata:
  short-description: "Playwright e2e UI proof"
user-invocable: true
---

# /playwright — browser automation (locadev)

**Two modes** (both use this skill family):

| Mode | Browser | Purpose |
|------|---------|---------|
| **Session (workflow default)** | `connectOverCDP` after `/chrome-debug-profile` | Boards, chat, PDF/Excel, internal tools — **no API keys** |
| **CI / app e2e** | Clean Chromium | Prove **your** app UI after implement → post-ready |

Org success pattern: chrome-debug + Playwright, then **site skills** for repeat flows. See `docs/browser-skills.md`.

Full discipline: `~/.grok/skills/playwright/SKILL.md`.

## Locadev rules

| Intent | Approach |
|--------|----------|
| Gather from signed-in UIs / chat / attachments | CDP + this skill or `/web-requirements` |
| Org-specific click paths | Site skill **on top of** chrome-debug + Playwright |
| Smoke / e2e the app under test | Clean Chromium e2e |
| Claim ready | `/grounding` with snapshot or e2e evidence |

## Quick path

1. Find `playwright.config.*` in the app package (or scaffold per user skill).
2. Prefer role + name selectors; avoid `waitForTimeout` spam.
3. Run: `npx playwright test` (from package that owns config).
4. Report pass/fail + coverage gaps.
5. Evidence for ready:

```bash
LOCADEV_READY_CLAIM='UI smoke green' \
LOCADEV_EVIDENCE='playwright: e2e smoke passed; verify:ok' \
  ./hooks/post-ready.sh
```

Do **not** use personal Chrome profile for CI e2e. See `docs/browser-skills.md`.
