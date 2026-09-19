# DAX measure library

Assumes `v_sales_detail` is imported and `dim_date` is related to `v_sales_detail[order_date]`.

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

Repeat Customers =
CALCULATE(
    DISTINCTCOUNT(v_customer_summary[customer_id]),
    v_customer_summary[is_repeat_customer] = TRUE()
)

Customers = DISTINCTCOUNT(v_customer_summary[customer_id])

Repeat Customer Rate = DIVIDE([Repeat Customers], [Customers])

Revenue LY =
CALCULATE(
    [Total Revenue],
    DATEADD(dim_date[calendar_date], -1, YEAR)
)

Revenue YoY % = DIVIDE([Total Revenue] - [Revenue LY], [Revenue LY])

Gross Profit LY =
CALCULATE(
    [Gross Profit],
    DATEADD(dim_date[calendar_date], -1, YEAR)
)

Gross Profit YoY % = DIVIDE([Gross Profit] - [Gross Profit LY], [Gross Profit LY])
```

Format revenue/profit/AOV as currency, margins/attainment/rates as percentages, and orders/units/customers as whole numbers.
