# DataLens — Nexa Retail: Data Quality Report

**Overall quality score: 95.17%**

| Table | Raw | Clean | Completeness | Uniqueness | RI | Validity | Score |
|---|---:|---:|---:|---:|---:|---:|---:|
| customers | 20,200 | 20,200 | 98.5% | 100.0% | 100.0% | 100.0% | 99.4% |
| products | 100 | 100 | 98.5% | 100.0% | 100.0% | 100.0% | 99.4% |
| stores | 22 | 22 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| orders | 150,000 | 149,256 | 66.7% | 100.0% | 100.0% | 99.9% | 86.6% |
| order_items | 284,367 | 284,367 | 85.6% | 100.0% | 100.0% | 100.0% | 94.2% |
| sales_targets | 490 | 24 | 78.3% | 100.0% | 100.0% | 100.0% | 91.3% |

## Controls
- Normalize categorical/text fields.
- Parse and constrain dates to 2024–2025.
- Remove duplicate business keys.
- Validate foreign keys against master tables.
- Null invalid quantities, discounts, prices, and costs.
- Preserve raw data for lineage; cleaned data is a separate layer.