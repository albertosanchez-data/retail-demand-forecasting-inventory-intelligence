
"""
Retail Demand Forecasting & Inventory Intelligence
Model 3: Global regression with historical mean and weekday features.

Training period: 2024-06-05 to 2024-06-11
Test period: 2024-06-12 to 2024-06-25

The original PostgreSQL data is accessed in read-only mode.
"""

import os
import getpass
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


# ---------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------

DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": os.getenv("PGPORT", "5432"),
    "dbname": "retail_demand_db",
    "user": os.getenv("PGUSER", "postgres"),
}

TRAIN_START = "2024-06-05"
TRAIN_END = "2024-06-11"
TEST_START = "2024-06-12"
TEST_END = "2024-06-25"

PROJECT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_DIR / "reports"
OUTPUT_FILE = REPORTS_DIR / "11_regression_forecast_metrics.csv"


# ---------------------------------------------------------
# 2. DATABASE QUERY
# ---------------------------------------------------------

QUERY = """
WITH daily_history AS (
    SELECT
        city_id,
        store_id,
        product_id,
        dt,
        sale_amount,
        AVG(sale_amount) OVER (
            PARTITION BY city_id, store_id, product_id
            ORDER BY dt
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        ) AS historical_mean
    FROM public.stg_retail_demand
    WHERE dt BETWEEN DATE '2024-05-29'
                 AND DATE '2024-06-25'
),
reference_stats AS (
    SELECT
        city_id,
        store_id,
        product_id,
        AVG(sale_amount) AS reference_mean
    FROM public.stg_retail_demand
    WHERE dt BETWEEN DATE '2024-06-05'
                 AND DATE '2024-06-11'
    GROUP BY
        city_id,
        store_id,
        product_id
)
SELECT
    d.city_id,
    d.store_id,
    d.product_id,
    d.dt,
    d.sale_amount,
    CASE
        WHEN d.dt BETWEEN DATE '2024-06-05'
                      AND DATE '2024-06-11'
            THEN d.historical_mean
        ELSE r.reference_mean
    END AS historical_mean
FROM daily_history AS d
INNER JOIN reference_stats AS r
    ON d.city_id = r.city_id
   AND d.store_id = r.store_id
   AND d.product_id = r.product_id
WHERE d.dt BETWEEN DATE '2024-06-05'
               AND DATE '2024-06-25'
ORDER BY
    d.dt,
    d.city_id,
    d.store_id,
    d.product_id;
"""


# ---------------------------------------------------------
# 3. LOAD DATA
# ---------------------------------------------------------

def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    password = os.getenv("PGPASSWORD")
    if not password:
        password = getpass.getpass("PostgreSQL password: ")

    connection = None

    try:
        connection = psycopg2.connect(
            **DB_CONFIG,
            password=password,
            options="-c default_transaction_read_only=on",
        )

        print("Connected to PostgreSQL in read-only mode.")
        print("Loading forecasting data...")

        df = pd.read_sql_query(QUERY, connection)

    finally:
        if connection is not None:
            connection.close()

    if df.empty:
        raise ValueError("The query returned no records.")

    df["dt"] = pd.to_datetime(df["dt"])
    df["sale_amount"] = pd.to_numeric(
        df["sale_amount"], errors="raise"
    )
    df["historical_mean"] = pd.to_numeric(
        df["historical_mean"], errors="raise"
    )

    if df["historical_mean"].isna().any():
        raise ValueError(
            "Historical mean contains missing values. "
            "Check the source data and historical windows."
        )

    print(f"Records loaded: {len(df):,}")
    print(
        f"Date range: {df['dt'].min().date()} to "
        f"{df['dt'].max().date()}"
    )


    # -----------------------------------------------------
    # 4. CHRONOLOGICAL TRAIN / TEST SPLIT
    # -----------------------------------------------------

    train = df[
        df["dt"].between(TRAIN_START, TRAIN_END)
    ].copy()

    test = df[
        df["dt"].between(TEST_START, TEST_END)
    ].copy()

    if train.empty or test.empty:
        raise ValueError("Training or test data is empty.")

    train_series = train[
        ["city_id", "store_id", "product_id"]
    ].drop_duplicates().shape[0]

    test_series = test[
        ["city_id", "store_id", "product_id"]
    ].drop_duplicates().shape[0]

    print(f"Training records: {len(train):,}")
    print(f"Test records: {len(test):,}")
    print(f"Training series: {train_series:,}")
    print(f"Test series: {test_series:,}")

    if len(train) != 350_000:
        raise ValueError(
            "Unexpected training record count. "
            "Expected 350,000 records."
        )

    if len(test) != 700_000:
        raise ValueError(
            "Unexpected test record count. "
            "Expected 700,000 records."
        )

    if train_series != 50_000 or test_series != 50_000:
        raise ValueError(
            "Unexpected number of time series. "
            "Expected 50,000 in both periods."
        )


    # -----------------------------------------------------
    # 5. FEATURES
    # -----------------------------------------------------
    # Training: previous seven days for each training date.
    # Test: June 5-11 mean held constant across the horizon.
    # Weekday is known in advance.
    # Actual test-period sales are never model inputs.

    feature_columns = ["historical_mean"]

    for day in range(7):
        column = f"weekday_{day}"

        train[column] = (
            train["dt"].dt.dayofweek == day
        ).astype(int)

        test[column] = (
            test["dt"].dt.dayofweek == day
        ).astype(int)

        feature_columns.append(column)

    X_train = train[feature_columns]
    y_train = train["sale_amount"]

    X_test = test[feature_columns]
    y_test = test["sale_amount"]


    # -----------------------------------------------------
    # 6. TRAIN REGRESSION MODEL
    # -----------------------------------------------------

    print("Training regression model...")

    model = HistGradientBoostingRegressor(
        max_iter=100,
        learning_rate=0.1,
        max_leaf_nodes=15,
        l2_regularization=1.0,
        random_state=42,
    )

    model.fit(X_train, y_train)

    print("Training completed.")


    # -----------------------------------------------------
    # 7. PREDICTIONS AND EVALUATION
    # -----------------------------------------------------

    predictions = model.predict(X_test)

    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))

    actual_total = y_test.sum()

    if actual_total == 0:
        wape = np.nan
    else:
        wape = (
            np.abs(y_test.to_numpy() - predictions).sum()
            / abs(actual_total)
            * 100
        )

    print("\n" + "=" * 55)
    print("REGRESSION FORECAST RESULTS")
    print("=" * 55)
    print(f"MAE: {mae:.6f}")
    print(f"RMSE: {rmse:.6f}")
    print(f"WAPE: {wape:.2f}%")
    print(f"Test records evaluated: {len(test):,}")


    # -----------------------------------------------------
    # 8. SAVE METRICS
    # -----------------------------------------------------

    results = pd.DataFrame([{
        "model": "hist_gradient_boosting_regression",
        "MAE": mae,
        "RMSE": rmse,
        "WAPE_percent": wape,
        "training_start": TRAIN_START,
        "training_end": TRAIN_END,
        "test_start": TEST_START,
        "test_end": TEST_END,
        "training_records": len(train),
        "test_records": len(test),
        "training_series": train_series,
        "test_series": test_series,
        "features": "historical_mean,weekday_one_hot",
    }])

    results.to_csv(OUTPUT_FILE, index=False)

    print(f"\nMetrics saved to:\n{OUTPUT_FILE}")
    print("\nOriginal source data was not modified.")


if __name__ == "__main__":
    main()
