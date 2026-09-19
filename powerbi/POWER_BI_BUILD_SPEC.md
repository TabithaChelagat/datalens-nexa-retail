# DataLens — Power BI Management Dashboard

Connect Power BI Desktop to PostgreSQL database `nexaretail`, schema `datalens`.

## Pages
### 1 — Executive Overview
KPI cards: Total Revenue, Gross Profit, Gross Margin %, Orders, Units, Average Order Value, Revenue Attainment %.

Visuals: monthly revenue line, actual vs target columns, revenue by region/store, revenue by category, store attainment table.

### 2 — Sales & Profitability
Revenue and gross profit trend, category revenue/profit, margin by category, discount analysis, monthly performance.

### 3 — Store Performance
Store ranking, revenue vs target, margin by store, orders by store, underperforming stores.

### 4 — Customer Analytics
Customers, repeat customers, repeat-customer rate, revenue per customer, order frequency.

### 5 — Data Quality
Row counts and null-key checks from `v_data_quality_summary`, plus the Phase 2 quality report.

## DAX measures
```DAX
Total Revenue = SUM(v_sales_detail[net_revenue])
Gross Profit = SUM(v_sales_detail[gross_profit])
Gross Margin % = DIVIDE([Gross Profit], [Total Revenue])
Orders = DISTINCTCOUNT(v_sales_detail[order_id])
Units = SUM(v_sales_detail[quantity])
Average Order Value = DIVIDE([Total Revenue], [Orders])
Target Revenue = SUM(v_target_attainment[revenue_target])
Actual Revenue = SUM(v_target_attainment[actual_revenue])
Revenue Attainment % = DIVIDE([Actual Revenue], [Target Revenue])
Repeat Customers = CALCULATE(DISTINCTCOUNT(v_customer_summary[customer_id]),v_customer_summary[is_repeat_customer]=TRUE())
Customers = DISTINCTCOUNT(v_customer_summary[customer_id])
Repeat Customer Rate = DIVIDE([Repeat Customers], [Customers])
```

Every KPI card should have a supporting visual. Use slicers for Year, Month, Region, Store and Category.
