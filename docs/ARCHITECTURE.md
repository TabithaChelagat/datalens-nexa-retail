# DataLens architecture

```text
                 Synthetic / source data
                           |
                           v
                Python quality pipeline
                           |
                           v
                    Cleaned datasets
                           |
                           v
                 PostgreSQL data model
                           |
                           v
                 Governed KPI views
                    /             \
                   /               \
                  v                 v
             Power BI          DataLens Agent
                                  |
                                  v
                         Natural-language UI
                                  |
                                  v
                         Evidence SQL/results
```

## Separation of responsibilities

- **Python:** profiling, cleaning, standardization and quality controls.
- **PostgreSQL:** governed storage, relational integrity and canonical KPI definitions.
- **Power BI:** management reporting and interactive visual analytics.
- **DataLens:** read-only natural-language analytics over approved views.
- **GitHub:** reproducible source, SQL, documentation and CI validation.

The agent does not become the source of truth. PostgreSQL views remain the source of truth for business KPIs.
