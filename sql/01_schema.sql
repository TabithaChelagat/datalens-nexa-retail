CREATE SCHEMA IF NOT EXISTS datalens;
DROP VIEW IF EXISTS datalens.v_customer_summary CASCADE;
DROP VIEW IF EXISTS datalens.v_data_quality_summary CASCADE;
DROP VIEW IF EXISTS datalens.v_target_attainment CASCADE;
DROP VIEW IF EXISTS datalens.v_category_performance CASCADE;
DROP VIEW IF EXISTS datalens.v_store_performance CASCADE;
DROP VIEW IF EXISTS datalens.v_monthly_kpis CASCADE;
DROP VIEW IF EXISTS datalens.v_sales_detail CASCADE;
DROP TABLE IF EXISTS datalens.fact_sales_target CASCADE;
DROP TABLE IF EXISTS datalens.fact_sales CASCADE;
DROP TABLE IF EXISTS datalens.fact_order CASCADE;
DROP TABLE IF EXISTS datalens.dim_date CASCADE;
DROP TABLE IF EXISTS datalens.dim_product CASCADE;
DROP TABLE IF EXISTS datalens.dim_store CASCADE;
DROP TABLE IF EXISTS datalens.dim_customer CASCADE;

CREATE TABLE datalens.dim_customer (
 customer_id TEXT PRIMARY KEY, customer_name TEXT, email TEXT, phone TEXT,
 gender TEXT, date_of_birth DATE, city TEXT, registration_date DATE
);
CREATE TABLE datalens.dim_product (
 product_id TEXT PRIMARY KEY, product_name TEXT NOT NULL, category TEXT,
 subcategory TEXT, unit_cost NUMERIC(12,2), selling_price NUMERIC(12,2)
);
CREATE TABLE datalens.dim_store (
 store_id TEXT PRIMARY KEY, store_name TEXT NOT NULL, region TEXT, city TEXT, manager TEXT
);
CREATE TABLE datalens.dim_date (
 date_key INTEGER PRIMARY KEY, calendar_date DATE UNIQUE NOT NULL, year INTEGER NOT NULL,
 quarter INTEGER NOT NULL, month_number INTEGER NOT NULL, month_name TEXT NOT NULL,
 year_month TEXT NOT NULL, week_number INTEGER NOT NULL, day_of_month INTEGER NOT NULL,
 day_name TEXT NOT NULL, is_weekend BOOLEAN NOT NULL
);
CREATE TABLE datalens.fact_order (
 order_id TEXT PRIMARY KEY, customer_id TEXT REFERENCES datalens.dim_customer(customer_id),
 store_id TEXT REFERENCES datalens.dim_store(store_id), order_date DATE,
 order_status TEXT, payment_method TEXT
);
CREATE TABLE datalens.fact_sales (
 order_item_id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES datalens.fact_order(order_id),
 product_id TEXT NOT NULL REFERENCES datalens.dim_product(product_id), quantity NUMERIC(12,2),
 unit_price NUMERIC(12,2), discount_pct NUMERIC(6,2), gross_revenue NUMERIC(14,2),
 net_revenue NUMERIC(14,2), estimated_cost NUMERIC(14,2), gross_profit NUMERIC(14,2)
);
CREATE TABLE datalens.fact_sales_target (
 target_id TEXT PRIMARY KEY, store_id TEXT NOT NULL REFERENCES datalens.dim_store(store_id),
 month DATE NOT NULL, revenue_target NUMERIC(14,2), profit_target NUMERIC(14,2),
 UNIQUE(store_id, month)
);
CREATE INDEX idx_order_date ON datalens.fact_order(order_date);
CREATE INDEX idx_order_customer ON datalens.fact_order(customer_id);
CREATE INDEX idx_order_store ON datalens.fact_order(store_id);
CREATE INDEX idx_sales_order ON datalens.fact_sales(order_id);
CREATE INDEX idx_sales_product ON datalens.fact_sales(product_id);
CREATE INDEX idx_target_month ON datalens.fact_sales_target(month);
