SELECT SUM(revenue) revenue FROM datalens.v_monthly_kpis WHERE month BETWEEN DATE '2025-01-01' AND DATE '2025-12-01';
SELECT store_name,region,revenue,gross_margin_pct FROM datalens.v_store_performance ORDER BY revenue DESC LIMIT 10;
SELECT store_name,region,month,revenue_target,actual_revenue,revenue_attainment_pct FROM datalens.v_target_attainment WHERE revenue_attainment_pct<1 ORDER BY revenue_attainment_pct;
SELECT category,revenue,gross_profit,gross_margin_pct FROM datalens.v_category_performance ORDER BY gross_profit DESC;
SELECT COUNT(*) customers,COUNT(*) FILTER(WHERE is_repeat_customer) repeat_customers,
       COUNT(*) FILTER(WHERE is_repeat_customer)::NUMERIC/NULLIF(COUNT(*),0) repeat_customer_rate
FROM datalens.v_customer_summary;
