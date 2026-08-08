# Project website (`docs/`)

Static landing page for **locadev**. No build step — pure HTML/CSS + logo.

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

Site URL:

```text
https://<username>.github.io/<repo-name>/
```

Example: repo `you/locadev` → `https://you.github.io/locadev/`

## Files

| File | Role |
|------|------|
| `index.html` | Landing page |
| `localdev-logo.jpg` | Logo (same as repo root) |

Colors match the logo wordmark: **Loca** orange `#ff9f1a`, **Dev** pink `#ff2d95`.
