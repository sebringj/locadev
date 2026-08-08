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

# /playwright — e2e UI proof (locadev)

**Means:** prove the **UI you built**. Feeds **`/grounding` post-ready**, not pre-decision research.

Full discipline: `~/.grok/skills/playwright/SKILL.md`.

## Locadev rules

| Intent | Skill |
|--------|-------|
| Gather product requirements from web | `/web-requirements` |
| Signed-in product docs | `/chrome-debug-profile` then `/web-requirements` |
| Smoke / e2e the app under test | **`/playwright`** (this) |
| Claim ready | `/grounding` post-ready with e2e evidence |

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
