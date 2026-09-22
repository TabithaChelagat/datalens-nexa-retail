# DataLens Phase 6 — Nexa Retail Demo

This deployment provides a dataset-backed, reproducible Nexa Retail analytics demo.

## Current milestone

- Loads a precomputed demo snapshot from `demo_data.json`.
- Displays revenue, gross profit, orders, customers, units, average order value, and gross margin.
- Displays monthly performance, category revenue, store performance, top products, and a data-quality summary.
- Shows methodology and data provenance.
- Keeps upload profiling as a separate experimental feature.

## Deployment

In Vercel, set the project Root Directory to `phase6`, then deploy.

## Data note

The demo snapshot is generated from the repository's `data/reference/*.csv` validated reference layer. This is intentional because the earlier generated cleaned order files contain invalidated identifier fields. The snapshot's methodology and source are displayed in the application.

## Scope

This milestone does not yet include hosted PostgreSQL or a natural-language KPI agent. Those are subsequent development stages.
