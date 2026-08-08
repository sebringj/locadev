# Project website (`docs/`)

Static landing page for **locadev**.

**Source of truth (always link here):** [github.com/sebringj/locadev](https://github.com/sebringj/locadev)

The site may be served from **GitHub Pages** or a **custom subdomain**. The page uses **absolute GitHub URLs** (clone, README, issues, boards/hooks docs) so a pretty domain never looks like a disconnected product without a repo.

**Positioning:** *You type. AI runs the rest.* — full AI workflow (gather via **browser skills** → clarify in Slack/Discord/Teams → **Jira + ADO boards** → `gh` PRs) + desk-hosted local cloud + **pre/post hooks**.

| Doc | Topic |
|-----|--------|
| [browser-skills.md](./browser-skills.md) | web-requirements vs chrome-debug-profile vs playwright |
| [../boards/README.md](../boards/README.md) | Jira + Azure DevOps |
| [../hooks/README.md](../hooks/README.md) | Pre/post grounding |

No build step — pure HTML/CSS + logo + **inline GitHub mark SVG** (no CDN).

## Preview locally (this works even before GitHub Pages)

From the **repo root**:

```bash
python3 -m http.server 8088 --directory docs
```

Then open: **http://127.0.0.1:8088/**

Or open the file directly:

```bash
open docs/index.html
```

If the browser says **failed to load page**:

| Cause | Fix |
|--------|-----|
| Nothing listening on the port | Run the `python3 -m http.server` command above |
| Wrong folder | Server must use `--directory docs` (not the repo root alone) |
| Opened a GitHub **blob** URL | HTML on `github.com/.../blob/...` is **not** a website — use Pages or local preview |
| GitHub Pages 404 | Enable Pages (below) and wait a few minutes after push |
| Placeholder `YOUR_ORG` 404s | Only needed if you still link to a fake GitHub org; page itself no longer depends on that |

## Enable GitHub Pages

1. Push `docs/` to your default branch  
2. Repo **Settings → Pages**  
3. **Source:** Deploy from a branch  
4. **Branch:** `main` (or default), folder: **`/docs`**  
5. Save  

Default Pages URL:

```text
https://sebringj.github.io/locadev/
```

### Custom subdomain

In the repo **Settings → Pages → Custom domain**, set your subdomain (e.g. `locadev.example.com`) and add the DNS CNAME GitHub shows. Optional: `docs/CNAME` file with that host.

The landing page already labels itself as the **product page** and points clone/issues/docs at **github.com/sebringj/locadev** so visitors aren’t stranded on a logo-only domain.

If the GitHub org/user ever renames, update absolute links in `docs/index.html` (search `sebringj/locadev`).

## Files

| File | Role |
|------|------|
| `index.html` | Landing page |
| `localdev-logo.jpg` | Logo (same as repo root) |

Colors match the logo wordmark: **Loca** orange `#ff9f1a`, **Dev** pink `#ff2d95`.
