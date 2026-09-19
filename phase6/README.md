# DataLens Phase 6 — Vercel Web App

This phase adds a Vercel-compatible web interface with:

- **Demo mode:** displays the Nexa Retail demo status.
- **Upload mode:** accepts CSV/XLSX/XLS files and generates an isolated profile.
- **No data mixing:** uploads are processed per request and are not inserted into the demo database.

## Deploy

1. Put the contents of this project in your GitHub repository.
2. In Vercel, choose **Add New → Project** and import the repository.
3. Set the **Root Directory** to `phase6` if this folder is nested in the repository.
4. Deploy. Vercel will detect `vercel.json` and install `requirements.txt`.

## Important scope

This is the first deployable vertical slice. It validates the web deployment and upload/profile workflow. The next iteration will connect the demo mode to hosted PostgreSQL and add the governed natural-language KPI agent.
