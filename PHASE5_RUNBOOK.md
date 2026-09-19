# Phase 5 — Standalone deployment & GitHub workflow

## What changed

Phase 5 turns DataLens from a collection of project files into a reproducible application stack:

`GitHub repository → Docker Compose → PostgreSQL → governed KPI views → Streamlit DataLens`

Power BI remains a separate BI consumer of the same governed PostgreSQL layer.

## Fast local demo

Prerequisites: Docker Desktop.

From the project root:

```bash
cd deploy
docker compose up --build
```

Open the Streamlit app at `http://localhost:8501`.

The database is initialized automatically from `data/cleaned/` on first database creation.

To stop:

```bash
docker compose down
```

To reset the database and reload all seed data:

```bash
docker compose down -v
docker compose up --build
```

## Optional LLM mode

Copy `deploy/.env.example` to `deploy/.env`, add an API key, and set a model available to your account. Never commit the key.

The deterministic governed-question mode works without an API key.

## GitHub

Push source code, SQL, documentation and the synthetic dataset. Do not push `.env`, database passwords, API keys, or Streamlit secrets.

Recommended repository description:

> AI-powered data quality, analytics and management assistant built on Python, PostgreSQL, SQL, Streamlit and Power BI.

## Deployment model

For a public demo, deploy the Streamlit container and use a managed PostgreSQL provider. Store `DATABASE_URL` and any LLM credentials as deployment secrets/environment variables.

Power BI connects separately to the managed PostgreSQL database.

## Security boundary

DataLens is intentionally read-only at the application layer. SQL is restricted to SELECT/WITH, one statement, no comments, and an allow-list of governed analytical views. Database credentials used by the app should also be granted read-only privileges in a production deployment.
