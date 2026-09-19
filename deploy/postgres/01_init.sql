-- DataLens local/standalone bootstrap for PostgreSQL.
-- Docker mounts the repository's cleaned CSV directory at /seed.
CREATE SCHEMA IF NOT EXISTS datalens;

-- Reuse the canonical project schema.
\i /project/sql/01_schema.sql

-- Load dimensions/facts using the actual identifier formats in the generated dataset.
\copy datalens.dim_customer FROM '/seed/customers_cleaned.csv' WITH (FORMAT csv, HEADER true, NULL '');
\copy datalens.dim_product FROM '/seed/products_cleaned.csv' WITH (FORMAT csv, HEADER true, NULL '');
\copy datalens.dim_store FROM '/seed/stores_cleaned.csv' WITH (FORMAT csv, HEADER true, NULL '');
\copy datalens.fact_order FROM '/seed/orders_cleaned.csv' WITH (FORMAT csv, HEADER true, NULL '');
\copy datalens.fact_sales_target(target_id,store_id,month,revenue_target,profit_target)
  FROM '/seed/sales_targets_cleaned.csv' WITH (FORMAT csv, HEADER true, NULL '');

INSERT INTO datalens.dim_date
SELECT TO_CHAR(d,'YYYYMMDD')::INTEGER, d::DATE, EXTRACT(YEAR FROM d)::INTEGER,
       EXTRACT(QUARTER FROM d)::INTEGER, EXTRACT(MONTH FROM d)::INTEGER,
       TO_CHAR(d,'FMMonth'), TO_CHAR(d,'YYYY-MM'), EXTRACT(WEEK FROM d)::INTEGER,
       EXTRACT(DAY FROM d)::INTEGER, TO_CHAR(d,'FMDay'), EXTRACT(ISODOW FROM d)::INTEGER IN (6,7)
FROM generate_series('2024-01-01'::DATE,'2025-12-31'::DATE,'1 day') g(d);

CREATE TEMP TABLE _order_items_import (
 order_item_id TEXT, order_id TEXT, product_id TEXT, quantity NUMERIC(12,2),
 unit_price NUMERIC(12,2), discount NUMERIC(12,2), discount_pct NUMERIC(6,2)
);
\copy _order_items_import FROM '/seed/order_items_cleaned.csv' WITH (FORMAT csv, HEADER true, NULL '');

INSERT INTO datalens.fact_sales
SELECT i.order_item_id, i.order_id, i.product_id, i.quantity,
       COALESCE(i.unit_price,p.selling_price), COALESCE(i.discount_pct,0),
       i.quantity * COALESCE(i.unit_price,p.selling_price),
       i.quantity * COALESCE(i.unit_price,p.selling_price) * (1-COALESCE(i.discount_pct,0)/100.0),
       i.quantity * COALESCE(p.unit_cost,0),
       i.quantity * COALESCE(i.unit_price,p.selling_price) * (1-COALESCE(i.discount_pct,0)/100.0)
         - i.quantity * COALESCE(p.unit_cost,0)
FROM _order_items_import i
JOIN datalens.dim_product p ON p.product_id=i.product_id
JOIN datalens.fact_order o ON o.order_id=i.order_id
WHERE i.order_id IS NOT NULL AND i.product_id IS NOT NULL AND i.quantity > 0;
DROP TABLE _order_items_import;

\i /project/sql/03_kpi_views.sql
