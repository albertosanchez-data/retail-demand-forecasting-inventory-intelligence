
import getpass
import os

import pandas as pd
import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "retail_demand_db",
    "user": "postgres",
    "options": "-c default_transaction_read_only=on",
    "connect_timeout": 10,
}

DB_CONFIG["password"] = getpass.getpass(
    "Current PostgreSQL password: "
)

query = """
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
    ROUND(SUM(sale_amount)::numeric, 2) AS total_sales,
    ROUND(AVG(sale_amount)::numeric, 4) AS average_sales_per_record,
    ROUND(
        SUM(sale_amount)::numeric / COUNT(DISTINCT dt),
        2
    ) AS average_daily_sales
FROM public.stg_retail_demand
WHERE product_id = 267
  AND dt BETWEEN DATE '2024-04-04' AND DATE '2024-06-25'
GROUP BY 1
ORDER BY 1;
"""

try:
    with psycopg2.connect(**DB_CONFIG) as conn:
        result = pd.read_sql_query(query, conn)

    print("\nPRODUCT 267 — DEMAND VALIDATION")
    print(result.to_string(index=False))
    print("\nValidation completed. No database changes made.")

except Exception as error:
    print(f"\nValidation failed: {error}")

finally:
    DB_CONFIG.pop("password", None)
