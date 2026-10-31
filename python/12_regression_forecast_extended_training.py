
"""
Retail Demand Forecasting & Inventory Intelligence
Model 4: Global regression with extended training history.

Training period: 2024-04-04 to 2024-06-11
Test period: 2024-06-12 to 2024-06-25

Historical features use only the seven days preceding each date.
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

TRAIN_START = "2024-04-04"
TRAIN_END = "2024-06-11"
TEST_START = "2024-06-12"
TEST_END = "2024-06-25"

PROJECT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_DIR / "reports"
OUTPUT_FILE = REPORTS_DIR / "12_regression_extended_metrics.csv"


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
    WHERE dt BETWEEN DATE '2024-03-28'
                 AND DATE '2024-06-25'
)
SELECT
    city_id,
    store_id,
    product_id,
    dt,
    sale_amount,
    historical_mean
FROM daily_history
WHERE dt BETWEEN DATE '2024-04-04'
             AND DATE '2024-06-25'
ORDER BY
    dt,
    city_id,
    store_id,
    product_id;
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

    if len(train) != 3_450_000:
        raise ValueError(
            "Unexpected training record count. "
            "Expected 3,450,000 records."
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
    # historical_mean uses the preceding seven days.
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
    print("EXTENDED-TRAINING REGRESSION RESULTS")
    print("=" * 55)
    print(f"MAE: {mae:.6f}")
    print(f"RMSE: {rmse:.6f}")
    print(f"WAPE: {wape:.2f}%")
    print(f"Training records evaluated: {len(train):,}")
    print(f"Test records evaluated: {len(test):,}")

    # -----------------------------------------------------
    # 8. SAVE METRICS
    # -----------------------------------------------------

    results = pd.DataFrame([{
        "model": "hist_gradient_boosting_extended_training",
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
    print("Original source data was not modified.")


if __name__ == "__main__":
    main()
