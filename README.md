# Ferozi.org — Static Site

Mockup-faithful rebuild of [ferozi.org](https://ferozi.org) from `D:\Projects\ferozi\ferozi html`.

## Local preview

```powershell
cd D:\Projects\feroziorg
npm install
npm run dev
```

Open **http://localhost:5173**

## Structure

- `web/` — deployable site (layout, CSS, PDFs, pages)
- `scripts/` — mirror, PDF generation, curation helpers
- `source/` / `site/` — large local FTP mirror / legacy dump (gitignored)

Publications are PDF downloads (generated from legacy Flash flipbook page scans).

Silsila / Shajra lineage pages are curated as HTML + PDF under `web/assets/pdfs/`.

FTP mirror scripts expect `FEROZI_FTP_PASS` (and optional host/user) in the environment — do not commit credentials.
