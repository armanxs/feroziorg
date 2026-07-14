# Ferozi.org — Static Site

Mockup-faithful rebuild of [ferozi.org](https://ferozi.org).

## Local preview

```powershell
cd D:\Projects\feroziorg
npm install
npm run dev
```

Open **http://localhost:5173**

## Cloudflare Pages

In the Pages project settings:

| Setting | Value |
|--------|--------|
| Framework preset | **None** |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Root directory | `/` (repo root) |
| Deploy command | **leave empty** |

Do **not** set the deploy command to `npx wrangler deploy` — that triggers Wrangler’s Vite auto-setup and breaks the build. Pages already publishes `dist` after a successful build.

## Structure

- `web/` — site source (HTML, CSS, JS, images, PDFs)
- `dist/` — production copy created by `npm run build`
- `scripts/` — mirror, PDF generation, curation helpers
- `source/` / `site/` — large local FTP mirror / legacy dump (gitignored)

FTP mirror scripts expect `FEROZI_FTP_PASS` in the environment — do not commit credentials.
