
-- ============================================================
-- PROJECT: Retail Demand Forecasting & Inventory Intelligence
-- FILE: 02_validate_loaded_data.sql
-- PURPOSE: Validate the PostgreSQL staging table after loading
-- ============================================================


-- 1. Confirm total rows and distinct business keys
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT (city_id, store_id, product_id, dt))
        AS distinct_business_keys
FROM public.stg_retail_demand;


-- 2. Validate the date range and number of observed dates
SELECT
    MIN(dt) AS first_date,
    MAX(dt) AS last_date,
    COUNT(DISTINCT dt) AS observed_days
FROM public.stg_retail_demand;


-- 3. Validate records per date
SELECT
    dt,
    COUNT(*) AS records_per_day,
    COUNT(DISTINCT product_id) AS distinct_products,
    COUNT(DISTINCT store_id) AS distinct_stores
FROM public.stg_retail_demand
GROUP BY dt
ORDER BY dt;


-- 4. Validate hourly array lengths
SELECT
    MIN(cardinality(hours_sale)) AS min_sales_hours,
    MAX(cardinality(hours_sale)) AS max_sales_hours,
    MIN(cardinality(hours_stock_status)) AS min_stock_hours,
    MAX(cardinality(hours_stock_status)) AS max_stock_hours
FROM public.stg_retail_demand;


-- 5. Review nulls in important analytical columns
SELECT
    COUNT(*) FILTER (WHERE dt IS NULL) AS null_dates,
    COUNT(*) FILTER (WHERE product_id IS NULL) AS null_products,
    COUNT(*) FILTER (WHERE store_id IS NULL) AS null_stores,
    COUNT(*) FILTER (WHERE sale_amount IS NULL) AS null_sales,
    COUNT(*) FILTER (WHERE discount IS NULL) AS null_discounts,
    COUNT(*) FILTER (WHERE stock_hour6_22_cnt IS NULL)
        AS null_stockout_counts
FROM public.stg_retail_demand;


-- 6. Review basic numeric ranges
SELECT
    MIN(sale_amount) AS min_sale_amount,
    MAX(sale_amount) AS max_sale_amount,
    AVG(sale_amount) AS avg_sale_amount,
    MIN(discount) AS min_discount,
    MAX(discount) AS max_discount,
    AVG(discount) AS avg_discount,
    MIN(stock_hour6_22_cnt) AS min_stockout_count,
    MAX(stock_hour6_22_cnt) AS max_stockout_count,
    AVG(stock_hour6_22_cnt) AS avg_stockout_count
FROM public.stg_retail_demand;

-- Investigate discount values greater than 1

SELECT
    COUNT(*) AS records_above_1,
    MIN(discount) AS minimum_discount_above_1,
    MAX(discount) AS maximum_discount_above_1,
    COUNT(DISTINCT product_id) AS affected_products,
    COUNT(DISTINCT city_id) AS affected_cities,
    COUNT(DISTINCT store_id) AS affected_stores
FROM public.stg_retail_demand
WHERE discount > 1;

-- Inspect individual records with discount greater than 1

SELECT
    dt,
    city_id,
    store_id,
    product_id,
    sale_amount,
    discount,
    stock_hour6_22_cnt
FROM public.stg_retail_demand
WHERE discount > 1
ORDER BY discount DESC, dt;