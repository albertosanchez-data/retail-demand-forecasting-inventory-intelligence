-- ============================================================
-- PROJECT: Retail Demand Forecasting & Inventory Intelligence
-- FILE: 03_daily_demand_analysis.sql
-- PURPOSE: Analyze daily normalized demand and stock status
-- ============================================================


-- ============================================================
-- 1. Daily normalized demand
-- ============================================================

SELECT
    dt,
    COUNT(*) AS product_store_records,
    ROUND(SUM(sale_amount)::numeric, 2)
        AS total_normalized_demand,
    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand_per_record
FROM public.stg_retail_demand
GROUP BY dt
ORDER BY dt;


-- ============================================================
-- 2. Average daily normalized demand by day of week
-- ============================================================

SELECT
    EXTRACT(ISODOW FROM dt)::INTEGER AS weekday_number,
    TO_CHAR(dt, 'FMDay') AS weekday_name,
    COUNT(*) AS observed_days,
    ROUND(AVG(daily_demand)::numeric, 2)
        AS avg_normalized_demand_per_day
FROM (
    SELECT
        dt,
        SUM(sale_amount) AS daily_demand
    FROM public.stg_retail_demand
    GROUP BY dt
) AS daily_totals
GROUP BY
    EXTRACT(ISODOW FROM dt),
    TO_CHAR(dt, 'FMDay')
ORDER BY weekday_number;


-- ============================================================
-- 3. Daily demand variability by day of week
-- ============================================================

WITH daily_totals AS (
    SELECT
        dt,
        SUM(sale_amount) AS daily_demand
    FROM public.stg_retail_demand
    GROUP BY dt
)
SELECT
    EXTRACT(ISODOW FROM dt)::INTEGER AS weekday_number,
    TO_CHAR(dt, 'FMDay') AS weekday_name,
    COUNT(*) AS observed_days,
    ROUND(AVG(daily_demand)::numeric, 2)
        AS avg_daily_normalized_demand,
    ROUND(MIN(daily_demand)::numeric, 2)
        AS min_daily_normalized_demand,
    ROUND(MAX(daily_demand)::numeric, 2)
        AS max_daily_normalized_demand,
    ROUND(STDDEV(daily_demand)::numeric, 2)
        AS stddev_daily_normalized_demand
FROM daily_totals
GROUP BY
    EXTRACT(ISODOW FROM dt),
    TO_CHAR(dt, 'FMDay')
ORDER BY weekday_number;


-- ============================================================
-- 4. Stock status hours count by day of week
-- ============================================================

SELECT
    EXTRACT(ISODOW FROM dt)::INTEGER AS weekday_number,
    TO_CHAR(dt, 'FMDay') AS weekday_name,
    COUNT(*) AS product_store_records,
    ROUND(AVG(stock_hour6_22_cnt)::numeric, 4)
        AS avg_stock_status_hours_count,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE stock_hour6_22_cnt > 0
        ) / COUNT(*)::numeric,
        2
    ) AS pct_records_with_positive_stock_status_count
FROM public.stg_retail_demand
GROUP BY
    EXTRACT(ISODOW FROM dt),
    TO_CHAR(dt, 'FMDay')
ORDER BY weekday_number;


-- ============================================================
-- 5. Product-level normalized demand and stock status
-- ============================================================

SELECT
    product_id,
    COUNT(*) AS product_store_days,
    ROUND(SUM(sale_amount)::numeric, 2)
        AS total_normalized_demand,
    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand_per_record,
    ROUND(AVG(stock_hour6_22_cnt)::numeric, 4)
        AS avg_stock_status_hours_count,
    COUNT(*) FILTER (
        WHERE stock_hour6_22_cnt > 0
    ) AS records_with_positive_stock_status_count,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE stock_hour6_22_cnt > 0
        ) / COUNT(*)::numeric,
        2
    ) AS pct_records_with_positive_stock_status_count
FROM public.stg_retail_demand
GROUP BY product_id
ORDER BY
    pct_records_with_positive_stock_status_count DESC,
    total_normalized_demand DESC
LIMIT 15;


-- ============================================================
-- 6. Product stock status with minimum record coverage
-- ============================================================

SELECT
    product_id,
    COUNT(*) AS product_store_records,
    COUNT(DISTINCT store_id) AS distinct_stores,
    COUNT(DISTINCT dt) AS observed_days,
    ROUND(SUM(sale_amount)::numeric, 2)
        AS total_normalized_demand,
    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand_per_record,
    ROUND(AVG(stock_hour6_22_cnt)::numeric, 4)
        AS avg_stock_status_hours_count,
    COUNT(*) FILTER (
        WHERE stock_hour6_22_cnt > 0
    ) AS records_with_positive_stock_status_count,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE stock_hour6_22_cnt > 0
        ) / COUNT(*)::numeric,
        2
    ) AS pct_records_with_positive_stock_status_count
FROM public.stg_retail_demand
GROUP BY product_id
HAVING COUNT(*) >= 500
ORDER BY
    pct_records_with_positive_stock_status_count DESC,
    product_store_records DESC
LIMIT 15;


-- ============================================================
-- 7. Normalized demand and stock status for selected products
-- ============================================================

SELECT
    product_id,
    COUNT(*) AS product_store_records,
    COUNT(DISTINCT store_id) AS distinct_stores,
    ROUND(MIN(sale_amount)::numeric, 4)
        AS min_normalized_demand,
    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand,
    ROUND(MAX(sale_amount)::numeric, 4)
        AS max_normalized_demand,
    MIN(stock_hour6_22_cnt)
        AS min_stock_status_hours_count,
    ROUND(AVG(stock_hour6_22_cnt)::numeric, 4)
        AS avg_stock_status_hours_count,
    MAX(stock_hour6_22_cnt)
        AS max_stock_status_hours_count
FROM public.stg_retail_demand
WHERE product_id IN (224, 267)
GROUP BY product_id
ORDER BY product_id;


-- ============================================================
-- 8. Stock status hours count distribution for selected products
-- ============================================================

SELECT
    product_id,
    stock_hour6_22_cnt,
    COUNT(*) AS record_count,
    ROUND(
        100.0 * COUNT(*) /
        SUM(COUNT(*)) OVER (
            PARTITION BY product_id
        ),
        2
    ) AS pct_product_records
FROM public.stg_retail_demand
WHERE product_id IN (224, 267)
GROUP BY
    product_id,
    stock_hour6_22_cnt
ORDER BY
    product_id,
    stock_hour6_22_cnt;


-- ============================================================
-- 9. Normalized demand by stock status hours count
-- ============================================================

SELECT
    product_id,
    stock_hour6_22_cnt,
    COUNT(*) AS product_store_records,
    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand,
    ROUND(MIN(sale_amount)::numeric, 4)
        AS min_normalized_demand,
    ROUND(MAX(sale_amount)::numeric, 4)
        AS max_normalized_demand
FROM public.stg_retail_demand
WHERE product_id IN (224, 267)
GROUP BY
    product_id,
    stock_hour6_22_cnt
ORDER BY
    product_id,
    stock_hour6_22_cnt;


-- ============================================================
-- 10. Product-level correlation between normalized demand
--     and stock status hours count
-- ============================================================

SELECT
    product_id,
    COUNT(*) AS product_store_records,
    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand,
    ROUND(AVG(stock_hour6_22_cnt)::numeric, 4)
        AS avg_stock_status_hours_count,
    ROUND(
        CORR(
            sale_amount,
            stock_hour6_22_cnt::double precision
        )::numeric,
        4
    ) AS demand_stock_status_correlation
FROM public.stg_retail_demand
GROUP BY product_id
HAVING COUNT(*) >= 500
ORDER BY demand_stock_status_correlation ASC NULLS LAST
LIMIT 15;


-- ============================================================
-- 11. Product 267: demand-stock status correlation by store
-- ============================================================

SELECT
    store_id,
    COUNT(*) AS observed_records,
    COUNT(DISTINCT dt) AS observed_days,
    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand,
    ROUND(AVG(stock_hour6_22_cnt)::numeric, 4)
        AS avg_stock_status_hours_count,
    ROUND(
        CORR(
            sale_amount,
            stock_hour6_22_cnt::double precision
        )::numeric,
        4
    ) AS demand_stock_status_correlation
FROM public.stg_retail_demand
WHERE product_id = 267
GROUP BY store_id
HAVING COUNT(*) >= 30
ORDER BY demand_stock_status_correlation ASC NULLS LAST;


-- ============================================================
-- 12. Product 267 daily observations in store 668
-- ============================================================

SELECT
    dt,
    sale_amount AS normalized_demand,
    stock_hour6_22_cnt AS stock_status_hours_count,
    discount,
    holiday_flag,
    activity_flag
FROM public.stg_retail_demand
WHERE product_id = 267
  AND store_id = 668
ORDER BY dt;


-- ============================================================
-- 13. Product 267: demand comparison across time periods
--     Store 668
-- ============================================================

SELECT
    CASE
        WHEN dt < DATE '2024-04-27'
            THEN '1. Before April 27'
        WHEN dt < DATE '2024-05-23'
            THEN '2. April 27 to May 22'
        ELSE '3. May 23 onward'
    END AS time_period,

    COUNT(*) AS observed_days,

    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand,

    ROUND(MIN(sale_amount)::numeric, 4)
        AS min_normalized_demand,

    ROUND(MAX(sale_amount)::numeric, 4)
        AS max_normalized_demand,

    ROUND(AVG(stock_hour6_22_cnt)::numeric, 4)
        AS avg_stock_status_hours_count,

    ROUND(
        CORR(
            sale_amount,
            stock_hour6_22_cnt::double precision
        )::numeric,
        4
    ) AS demand_stock_status_correlation

FROM public.stg_retail_demand
WHERE product_id = 267
  AND store_id = 668
GROUP BY
    CASE
        WHEN dt < DATE '2024-04-27'
            THEN '1. Before April 27'
        WHEN dt < DATE '2024-05-23'
            THEN '2. April 27 to May 22'
        ELSE '3. May 23 onward'
    END
ORDER BY time_period;


-- ============================================================
-- 14. Product 267: normalized demand across stores and periods
-- ============================================================

WITH store_period_sales AS (
    SELECT
        store_id,

        CASE
            WHEN dt < DATE '2024-04-27'
                THEN '1. Before April 27'
            WHEN dt < DATE '2024-05-23'
                THEN '2. April 27 to May 22'
            ELSE '3. May 23 onward'
        END AS time_period,

        COUNT(*) AS observed_days,
        AVG(sale_amount) AS avg_normalized_demand,
        AVG(stock_hour6_22_cnt) AS avg_stock_status_hours_count

    FROM public.stg_retail_demand
    WHERE product_id = 267
    GROUP BY
        store_id,
        CASE
            WHEN dt < DATE '2024-04-27'
                THEN '1. Before April 27'
            WHEN dt < DATE '2024-05-23'
                THEN '2. April 27 to May 22'
            ELSE '3. May 23 onward'
        END
)

SELECT
    time_period,
    COUNT(*) AS stores,
    SUM(observed_days) AS total_store_day_records,

    ROUND(AVG(avg_normalized_demand)::numeric, 4)
        AS avg_demand_across_stores,

    ROUND(AVG(avg_stock_status_hours_count)::numeric, 4)
        AS avg_stock_status_count_across_stores

FROM store_period_sales
GROUP BY time_period
ORDER BY time_period;


-- ============================================================
-- 15. Product 267: daily normalized demand and stock status
-- ============================================================

SELECT
    dt,
    COUNT(*) AS store_records,

    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand_per_store,

    ROUND(SUM(sale_amount)::numeric, 4)
        AS total_normalized_demand,

    ROUND(AVG(stock_hour6_22_cnt)::numeric, 4)
        AS avg_stock_status_hours_count,

    COUNT(*) FILTER (
        WHERE stock_hour6_22_cnt = 0
    ) AS records_with_zero_stock_status_count,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE stock_hour6_22_cnt = 0
        ) / COUNT(*),
        2
    ) AS pct_records_with_zero_stock_status_count

FROM public.stg_retail_demand
WHERE product_id = 267
GROUP BY dt
ORDER BY dt;


-- ============================================================
-- 16. April 27 demand change across all products
-- ============================================================

SELECT
    dt,
    COUNT(*) AS product_store_records,
    COUNT(DISTINCT product_id) AS distinct_products,

    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand_per_record,

    ROUND(SUM(sale_amount)::numeric, 2)
        AS total_normalized_demand,

    ROUND(AVG(stock_hour6_22_cnt)::numeric, 4)
        AS avg_stock_status_hours_count

FROM public.stg_retail_demand
WHERE dt BETWEEN DATE '2024-04-23'
             AND DATE '2024-05-01'
GROUP BY dt
ORDER BY dt;


-- ============================================================
-- 17. Product-level demand change: April 26 vs April 27
-- ============================================================

WITH daily_product_sales AS (
    SELECT
        product_id,
        dt,
        AVG(sale_amount) AS avg_normalized_demand
    FROM public.stg_retail_demand
    WHERE dt IN (
        DATE '2024-04-26',
        DATE '2024-04-27'
    )
    GROUP BY product_id, dt
),

product_comparison AS (
    SELECT
        product_id,

        MAX(avg_normalized_demand) FILTER (
            WHERE dt = DATE '2024-04-26'
        ) AS demand_apr_26,

        MAX(avg_normalized_demand) FILTER (
            WHERE dt = DATE '2024-04-27'
        ) AS demand_apr_27

    FROM daily_product_sales
    GROUP BY product_id
)

SELECT
    product_id,

    ROUND(demand_apr_26::numeric, 4)
        AS demand_apr_26,

    ROUND(demand_apr_27::numeric, 4)
        AS demand_apr_27,

    ROUND(
        (demand_apr_27 - demand_apr_26)::numeric,
        4
    ) AS absolute_change,

    ROUND(
        (
            100.0 * (demand_apr_27 - demand_apr_26)
            / NULLIF(demand_apr_26, 0)
        )::numeric,
        2
    ) AS pct_change

FROM product_comparison
WHERE demand_apr_26 IS NOT NULL
  AND demand_apr_27 IS NOT NULL
ORDER BY pct_change DESC NULLS LAST;


-- ============================================================
-- 18. Classification of product demand changes
--     April 26 vs April 27, 2024
-- ============================================================

WITH daily_product_sales AS (
    SELECT
        product_id,
        dt,
        AVG(sale_amount) AS avg_normalized_demand
    FROM public.stg_retail_demand
    WHERE dt IN (
        DATE '2024-04-26',
        DATE '2024-04-27'
    )
    GROUP BY product_id, dt
),

product_comparison AS (
    SELECT
        product_id,

        MAX(avg_normalized_demand) FILTER (
            WHERE dt = DATE '2024-04-26'
        ) AS demand_apr_26,

        MAX(avg_normalized_demand) FILTER (
            WHERE dt = DATE '2024-04-27'
        ) AS demand_apr_27

    FROM daily_product_sales
    GROUP BY product_id
),

classified_products AS (
    SELECT
        product_id,
        demand_apr_26,
        demand_apr_27,

        CASE
            WHEN demand_apr_26 = 0
                THEN 'Base equal to zero'

            WHEN demand_apr_27 >= demand_apr_26 * 6
                THEN 'Increase greater than 500%'

            WHEN demand_apr_27 >= demand_apr_26 * 3
                THEN 'Increase greater than 200%'

            WHEN demand_apr_27 >= demand_apr_26 * 2
                THEN 'Increase greater than 100%'

            WHEN demand_apr_27 <= demand_apr_26 * 0.5
                THEN 'Decrease greater than 50%'

            ELSE 'Remaining change'
        END AS change_category

    FROM product_comparison
    WHERE demand_apr_26 IS NOT NULL
      AND demand_apr_27 IS NOT NULL
)

SELECT
    change_category,
    COUNT(*) AS product_count
FROM classified_products
GROUP BY change_category
ORDER BY product_count DESC;


-- ============================================================
-- 19. Context of product 267 demand change
--     April 25–28, 2024
-- ============================================================

SELECT
    dt,
    COUNT(*) AS store_records,

    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand,

    ROUND(AVG(discount)::numeric, 4)
        AS avg_discount,

    SUM(CASE
        WHEN discount > 0 THEN 1
        ELSE 0
    END) AS records_with_discount,

    SUM(CASE
        WHEN activity_flag = 1 THEN 1
        ELSE 0
    END) AS records_with_activity,

    SUM(CASE
        WHEN holiday_flag = 1 THEN 1
        ELSE 0
    END) AS records_marked_as_holiday,

    ROUND(AVG(stock_hour6_22_cnt)::numeric, 4)
        AS avg_stock_status_hours_count

FROM public.stg_retail_demand
WHERE product_id = 267
  AND dt IN (
      DATE '2024-04-25',
      DATE '2024-04-26',
      DATE '2024-04-27',
      DATE '2024-04-28'
  )
GROUP BY dt
ORDER BY dt;


-- ============================================================
-- 20. Normalized demand comparison by holiday flag
-- ============================================================

SELECT
    holiday_flag,
    COUNT(*) AS total_records,
    COUNT(DISTINCT product_id) AS distinct_products,
    COUNT(DISTINCT dt) AS distinct_dates,

    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand,

    ROUND(SUM(sale_amount)::numeric, 2)
        AS total_normalized_demand,

    ROUND(AVG(stock_hour6_22_cnt)::numeric, 4)
        AS avg_stock_status_hours_count,

    ROUND(AVG(discount)::numeric, 4)
        AS avg_discount

FROM public.stg_retail_demand
GROUP BY holiday_flag
ORDER BY holiday_flag;


-- ============================================================
-- 21. Inspect dates marked as holidays
-- ============================================================

SELECT
    dt,
    COUNT(*) AS total_records,
    COUNT(DISTINCT product_id) AS distinct_products,

    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand,

    ROUND(AVG(stock_hour6_22_cnt)::numeric, 4)
        AS avg_stock_status_hours_count

FROM public.stg_retail_demand
WHERE holiday_flag = 1
GROUP BY dt
ORDER BY dt;


-- ============================================================
-- 22. Holiday flag distribution by weekday
-- ============================================================

WITH daily_flags AS (
    SELECT
        dt,
        EXTRACT(ISODOW FROM dt)::INTEGER AS weekday_number,
        TO_CHAR(dt, 'FMDay') AS weekday_name,
        MAX(holiday_flag) AS holiday_flag
    FROM public.stg_retail_demand
    GROUP BY dt
)

SELECT
    weekday_number,
    weekday_name,
    COUNT(*) AS total_dates,

    SUM(
        CASE WHEN holiday_flag = 1 THEN 1 ELSE 0 END
    ) AS holiday_dates,

    SUM(
        CASE WHEN holiday_flag = 0 THEN 1 ELSE 0 END
    ) AS non_holiday_dates,

    ROUND(
        (
            100.0 * SUM(
                CASE WHEN holiday_flag = 1 THEN 1 ELSE 0 END
            ) / COUNT(*)
        )::numeric,
        2
    ) AS pct_dates_marked_holiday

FROM daily_flags
GROUP BY weekday_number, weekday_name
ORDER BY weekday_number;


-- ============================================================
-- 23. Normalized demand by weekday and holiday flag
-- ============================================================

WITH daily_sales AS (
    SELECT
        dt,
        EXTRACT(ISODOW FROM dt)::INTEGER AS weekday_number,
        TO_CHAR(dt, 'FMDay') AS weekday_name,
        MAX(holiday_flag) AS holiday_flag,
        AVG(sale_amount) AS avg_daily_demand_per_record
    FROM public.stg_retail_demand
    GROUP BY dt
)

SELECT
    weekday_number,
    weekday_name,
    holiday_flag,
    COUNT(*) AS number_of_dates,

    ROUND(
        AVG(avg_daily_demand_per_record)::numeric,
        4
    ) AS avg_normalized_demand_per_record

FROM daily_sales
GROUP BY
    weekday_number,
    weekday_name,
    holiday_flag
ORDER BY
    weekday_number,
    holiday_flag;


-- ============================================================
-- 24. Product 267: training and test period coverage
-- ============================================================

SELECT
    CASE
        WHEN dt BETWEEN DATE '2024-04-04' AND DATE '2024-06-11'
            THEN 'Training'
        WHEN dt BETWEEN DATE '2024-06-12' AND DATE '2024-06-25'
            THEN 'Test'
    END AS period,

    MIN(dt) AS start_date,
    MAX(dt) AS end_date,
    COUNT(*) AS records,
    COUNT(DISTINCT city_id) AS cities,
    COUNT(DISTINCT store_id) AS stores,

    ROUND(SUM(sale_amount)::numeric, 2)
        AS total_normalized_demand,

    ROUND(AVG(sale_amount)::numeric, 4)
        AS avg_normalized_demand_per_record,

    ROUND(
        SUM(sale_amount)::numeric
        / COUNT(DISTINCT dt),
        2
    ) AS avg_daily_normalized_demand

FROM public.stg_retail_demand
WHERE product_id = 267
  AND dt BETWEEN DATE '2024-04-04' AND DATE '2024-06-25'
GROUP BY
    CASE
        WHEN dt BETWEEN DATE '2024-04-04' AND DATE '2024-06-11'
            THEN 'Training'
        WHEN dt BETWEEN DATE '2024-06-12' AND DATE '2024-06-25'
            THEN 'Test'
    END
ORDER BY period;