CREATE OR REPLACE VIEW datalens.v_sales_detail AS
SELECT o.order_id,o.order_date,o.customer_id,o.store_id,s.store_name,s.region,s.city AS store_city,
       i.order_item_id,p.product_id,p.product_name,p.category,p.subcategory,i.quantity,i.unit_price,
       i.discount_pct,i.gross_revenue,i.net_revenue,i.estimated_cost,i.gross_profit,
       CASE WHEN i.net_revenue<>0 THEN i.gross_profit/i.net_revenue END AS gross_margin_pct,
       o.order_status,o.payment_method
FROM datalens.fact_sales i
JOIN datalens.fact_order o ON o.order_id=i.order_id
JOIN datalens.dim_store s ON s.store_id=o.store_id
JOIN datalens.dim_product p ON p.product_id=i.product_id;

CREATE OR REPLACE VIEW datalens.v_monthly_kpis AS
SELECT DATE_TRUNC('month',o.order_date)::DATE month,
       SUM(i.net_revenue) revenue,SUM(i.gross_profit) gross_profit,
       CASE WHEN SUM(i.net_revenue)<>0 THEN SUM(i.gross_profit)/SUM(i.net_revenue) END gross_margin_pct,
       COUNT(DISTINCT o.order_id) orders,SUM(i.quantity) units,
       CASE WHEN COUNT(DISTINCT o.order_id)>0 THEN SUM(i.net_revenue)/COUNT(DISTINCT o.order_id) END average_order_value
FROM datalens.fact_order o JOIN datalens.fact_sales i ON i.order_id=o.order_id
WHERE o.order_status NOT IN ('Cancelled','Returned') AND o.order_date IS NOT NULL
GROUP BY 1;

CREATE OR REPLACE VIEW datalens.v_store_performance AS
SELECT s.store_id,s.store_name,s.region,s.city,
       SUM(i.net_revenue) revenue,SUM(i.gross_profit) gross_profit,
       COUNT(DISTINCT o.order_id) orders,SUM(i.quantity) units,
       CASE WHEN SUM(i.net_revenue)<>0 THEN SUM(i.gross_profit)/SUM(i.net_revenue) END gross_margin_pct
FROM datalens.dim_store s JOIN datalens.fact_order o ON o.store_id=s.store_id
JOIN datalens.fact_sales i ON i.order_id=o.order_id
WHERE o.order_status NOT IN ('Cancelled','Returned') GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW datalens.v_category_performance AS
SELECT p.category,SUM(i.net_revenue) revenue,SUM(i.gross_profit) gross_profit,
       SUM(i.quantity) units,COUNT(DISTINCT o.order_id) orders,
       CASE WHEN SUM(i.net_revenue)<>0 THEN SUM(i.gross_profit)/SUM(i.net_revenue) END gross_margin_pct
FROM datalens.fact_sales i JOIN datalens.fact_order o ON o.order_id=i.order_id
JOIN datalens.dim_product p ON p.product_id=i.product_id
WHERE o.order_status NOT IN ('Cancelled','Returned') GROUP BY 1;

CREATE OR REPLACE VIEW datalens.v_target_attainment AS
WITH actual AS (
 SELECT o.store_id,DATE_TRUNC('month',o.order_date)::DATE month,SUM(i.net_revenue) actual_revenue,
        SUM(i.gross_profit) actual_profit,COUNT(DISTINCT o.order_id) actual_orders
 FROM datalens.fact_order o JOIN datalens.fact_sales i ON i.order_id=o.order_id
 WHERE o.order_status NOT IN ('Cancelled','Returned') GROUP BY 1,2)
SELECT t.target_id,t.month,t.store_id,s.store_name,s.region,t.revenue_target,t.profit_target,
       COALESCE(a.actual_revenue,0) actual_revenue,COALESCE(a.actual_profit,0) actual_profit,
       COALESCE(a.actual_orders,0) actual_orders,
       CASE WHEN t.revenue_target>0 THEN COALESCE(a.actual_revenue,0)/t.revenue_target END revenue_attainment_pct,
       CASE WHEN t.profit_target>0 THEN COALESCE(a.actual_profit,0)/t.profit_target END profit_attainment_pct
FROM datalens.fact_sales_target t JOIN datalens.dim_store s ON s.store_id=t.store_id
LEFT JOIN actual a ON a.store_id=t.store_id AND a.month=t.month;

CREATE OR REPLACE VIEW datalens.v_customer_summary AS
WITH x AS (
 SELECT o.customer_id,COUNT(DISTINCT o.order_id) orders,SUM(i.net_revenue) revenue,
        MIN(o.order_date) first_order_date,MAX(o.order_date) last_order_date
 FROM datalens.fact_order o JOIN datalens.fact_sales i ON i.order_id=o.order_id
 WHERE o.order_status NOT IN ('Cancelled','Returned') GROUP BY 1)
SELECT c.customer_id,c.customer_name,c.city,c.gender,COALESCE(x.orders,0) orders,
       COALESCE(x.revenue,0) revenue,x.first_order_date,x.last_order_date,
       (COALESCE(x.orders,0)>=2) is_repeat_customer
FROM datalens.dim_customer c LEFT JOIN x ON x.customer_id=c.customer_id;

CREATE OR REPLACE VIEW datalens.v_data_quality_summary AS
SELECT 'dim_customer' table_name,COUNT(*) row_count,COUNT(*) FILTER(WHERE customer_id IS NULL) null_key_count FROM datalens.dim_customer
UNION ALL SELECT 'dim_product',COUNT(*),COUNT(*) FILTER(WHERE product_id IS NULL) FROM datalens.dim_product
UNION ALL SELECT 'dim_store',COUNT(*),COUNT(*) FILTER(WHERE store_id IS NULL) FROM datalens.dim_store
UNION ALL SELECT 'fact_order',COUNT(*),COUNT(*) FILTER(WHERE order_id IS NULL) FROM datalens.fact_order
UNION ALL SELECT 'fact_sales',COUNT(*),COUNT(*) FILTER(WHERE order_item_id IS NULL OR order_id IS NULL OR product_id IS NULL) FROM datalens.fact_sales
UNION ALL SELECT 'fact_sales_target',COUNT(*),COUNT(*) FILTER(WHERE target_id IS NULL OR store_id IS NULL) FROM datalens.fact_sales_target;
