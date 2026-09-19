# DataLens — AI-Powered Data Quality, Analytics & Management Assistant

## Business problem
Nexa Retail receives operational data containing duplicates, missing values, inconsistent labels, invalid foreign keys and transaction anomalies. Management needs trusted sales and profitability reporting, while analysts need a repeatable data-management process rather than spreadsheet-only fixes.

## Solution
DataLens creates a governed path from raw data to management insight:

`Raw CSV → profiling & validation → cleaning → PostgreSQL model → governed KPI views → Power BI + AI assistant`

The same PostgreSQL KPI definitions feed both BI and the assistant. The AI layer is read-only and can only query approved analytical views.

## Demonstrated skills
- Python/Pandas data profiling and cleaning
- Data-quality controls and exception handling
- Deduplication and referential-integrity validation
- PostgreSQL dimensional/fact modeling
- SQL KPI engineering and metric governance
- Power BI semantic modeling and DAX
- Streamlit application development
- Natural-language analytics with optional LLM-to-SQL translation
- Read-only SQL safety controls and evidence SQL
- Data lineage and reproducible documentation

## Analytics delivered
Revenue, gross profit, gross margin, orders, units, average order value, target attainment, YoY trends, store performance, category performance and repeat-customer rate.

## AI design
The assistant is evidence-first: it returns the result set and the SQL used to produce it. Deterministic templates cover common management questions without an API key. Optional LLM mode translates broader natural-language questions into SQL, after which the application validates the query against a strict read-only allow-list.

## Why this is a Data Analyst + Data Manager portfolio project
The project demonstrates more than dashboard creation. It shows how an analyst can establish trustworthy data inputs, define metrics centrally, preserve lineage, build reusable analytical structures, and expose those structures safely to business users and AI systems.
