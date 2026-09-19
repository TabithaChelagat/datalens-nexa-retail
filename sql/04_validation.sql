-- All failure counts should be 0.
SELECT 'customer_pk_failed' test, COUNT(*)-COUNT(DISTINCT customer_id) failures FROM datalens.dim_customer
UNION ALL SELECT 'product_pk_failed',COUNT(*)-COUNT(DISTINCT product_id) FROM datalens.dim_product
UNION ALL SELECT 'store_pk_failed',COUNT(*)-COUNT(DISTINCT store_id) FROM datalens.dim_store
UNION ALL SELECT 'order_pk_failed',COUNT(*)-COUNT(DISTINCT order_id) FROM datalens.fact_order
UNION ALL SELECT 'sales_order_fk_failed',COUNT(*) FROM datalens.fact_sales f LEFT JOIN datalens.fact_order o ON o.order_id=f.order_id WHERE o.order_id IS NULL
UNION ALL SELECT 'sales_product_fk_failed',COUNT(*) FROM datalens.fact_sales f LEFT JOIN datalens.dim_product p ON p.product_id=f.product_id WHERE p.product_id IS NULL
UNION ALL SELECT 'negative_quantity_failed',COUNT(*) FROM datalens.fact_sales WHERE quantity<=0
UNION ALL SELECT 'negative_net_revenue_failed',COUNT(*) FROM datalens.fact_sales WHERE net_revenue<0
UNION ALL SELECT 'target_duplicate_failed',COUNT(*)-COUNT(DISTINCT(store_id,month)) FROM datalens.fact_sales_target;
