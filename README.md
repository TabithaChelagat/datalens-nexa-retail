# DataLens — Nexa Retail

AI-powered Data Quality, Analytics & Management Assistant.

## Build order

1. Synthetic raw/reference data
2. Data profiling and quality validation
3. Cleaning pipeline
4. PostgreSQL analytical model
5. SQL KPI layer
6. Power BI management dashboard
7. Analytical agent
8. Portfolio documentation

## Data period

2024-01-01 to 2025-12-31.

## Raw data

The `data/raw/` files intentionally contain controlled data-quality defects.

## Reference data

The `data/reference/` files are clean ground truth used to validate the data-quality pipeline.

## Quality benchmark

`data/quality/injected_quality_benchmark.json` records the intentionally injected defects.

## Principle

The AI agent must use computed database results and analytical functions as evidence. It should not invent business metrics.

## Standalone application

DataLens can be run locally as a two-container stack with Docker Compose. PostgreSQL is initialized automatically from the cleaned CSVs and the canonical SQL model/views. The Streamlit agent then connects to that database over the internal Docker network.

```bash
cd deploy
docker compose up --build
```

Open `http://localhost:8501`.

See `PHASE5_RUNBOOK.md` for deployment, GitHub and production guidance.
