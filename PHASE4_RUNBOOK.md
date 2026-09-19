# Phase 4 runbook

## 1. Build PostgreSQL
Create database `nexaretail`, then run Phase 3 scripts in this order:
1. `sql/01_schema.sql`
2. Edit `sql/02_load_cleaned_data.sql` and replace `REPLACE_WITH_ABSOLUTE_PATH_TO_DATA_CLEANED` with the absolute path to `data/cleaned`.
3. `sql/02_load_cleaned_data.sql`
4. `sql/03_kpi_views.sql`
5. `sql/04_validation.sql`

## 2. Install the agent
From `agent/`:

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Configure
Copy `.env.example` to `.env` or set environment variables. At minimum:

`DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/nexaretail`

`OPENAI_API_KEY` is optional. The governed-question mode works without it.

## 4. Run
```bash
streamlit run app.py
```

## 5. Connect Power BI
Import `datalens.dim_date` and the governed analytical views. Create the date relationship described in `powerbi/DASHBOARD_BUILD.md`, then implement `powerbi/DAX_MEASURES.md`.

## 6. Security
- Never commit `.env` or API keys.
- Use a PostgreSQL read-only user for the Streamlit agent.
- Keep the agent restricted to approved views.
- Do not expose raw operational tables to the LLM.
