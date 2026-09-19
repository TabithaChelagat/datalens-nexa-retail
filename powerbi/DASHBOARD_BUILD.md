# DataLens Power BI build

## Semantic model
Import `datalens.dim_date` plus the governed views. Create a one-to-many relationship:
- `dim_date[calendar_date]` → `v_sales_detail[order_date]`

Use the governed views for business KPIs. Do not recreate KPI logic differently in Power BI.

## Page 1 — Executive Overview
- Cards: Total Revenue, Gross Profit, Gross Margin %, Orders, Units, Average Order Value, Revenue Attainment %
- Line: monthly Revenue and Gross Profit
- Clustered column: Actual Revenue vs Target by Store
- Bar: Revenue by Category
- Bar/map alternative: Revenue by Region
- Matrix: Store, Revenue, Gross Profit, Margin %, Attainment %
- Slicers: Year, Month, Region, Store, Category

## Page 2 — Sales & Profitability
Revenue, gross profit, margin, orders and units by month/category/product. Add YoY measures.

## Page 3 — Store Performance
Rank stores by revenue, profit, margin and target attainment. Highlight stores below 100% attainment.

## Page 4 — Customer Analytics
Customers, repeat customers, repeat-customer rate, customer revenue distribution and city breakdown.

## Page 5 — Data Quality
Use `v_data_quality_summary` for row counts and null-key counts. Add a table of quality-control results from the Phase 2 report.

## Design rule
Every KPI card must have at least one supporting visual so management can see the driver behind the number.
