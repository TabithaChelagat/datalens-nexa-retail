# DataLens — Phase 3 Setup

## 1. Create database
`CREATE DATABASE nexaretail;`

## 2. Execute SQL in order
1. `sql/01_schema.sql`
2. Edit `sql/02_load_cleaned_data.sql` and replace the DATA_PATH placeholder.
3. `sql/02_load_cleaned_data.sql`
4. `sql/03_kpi_views.sql`
5. `sql/04_validation.sql`

## 3. Validation
Every failure count must be 0.

## 4. Power BI
Connect to PostgreSQL and import the governed views described in `powerbi/POWER_BI_BUILD_SPEC.md`.

## 5. Agent
The future DataLens agent must use the same PostgreSQL views as Power BI. This prevents the dashboard and chatbot from using conflicting KPI definitions.

Architecture:
Raw CSV → Data quality/cleaning → PostgreSQL governed model → KPI views → Power BI + AI agent
