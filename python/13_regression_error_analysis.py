
"""
Retail Demand Forecasting & Inventory Intelligence
Model 4: Regression error analysis.

Training period: 2024-04-04 to 2024-06-11
Test period: 2024-06-12 to 2024-06-25

The source database is accessed in read-only mode.
This script analyzes test errors without modifying source data.
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

ERRORS_FILE = REPORTS_DIR / "13_regression_test_errors.csv"
SUMMARY_FILE = REPORTS_DIR / "13_regression_error_summary.csv"
DAILY_FILE = REPORTS_DIR / "13_regression_daily_errors.csv"


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
        print("Loading data for error analysis...")

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
            "Historical mean contains missing values."
        )

    # -----------------------------------------------------
    # 4. CHRONOLOGICAL SPLIT
    # -----------------------------------------------------

    train = df[
        df["dt"].between(TRAIN_START, TRAIN_END)
    ].copy()

    test = df[
        df["dt"].between(TEST_START, TEST_END)
    ].copy()

    if len(train) != 3_450_000:
        raise ValueError(
            f"Expected 3,450,000 training rows; found {len(train):,}."
        )

    if len(test) != 700_000:
        raise ValueError(
            f"Expected 700,000 test rows; found {len(test):,}."
        )

    print(f"Training records: {len(train):,}")
    print(f"Test records: {len(test):,}")

    # -----------------------------------------------------
    # 5. FEATURES AND MODEL
    # -----------------------------------------------------

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

    print("Training regression model for error analysis...")

    model = HistGradientBoostingRegressor(
        max_iter=100,
        learning_rate=0.1,
        max_leaf_nodes=15,
        l2_regularization=1.0,
        random_state=42,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    # -----------------------------------------------------
    # 6. RECORD-LEVEL ERRORS
    # -----------------------------------------------------

    errors = test[
        ["city_id", "store_id", "product_id", "dt", "sale_amount"]
    ].copy()

    errors = errors.rename(
        columns={"sale_amount": "actual_sales"}
    )

    errors["predicted_sales"] = predictions
    errors["error"] = (
        errors["actual_sales"] - errors["predicted_sales"]
    )
    errors["absolute_error"] = errors["error"].abs()
    errors["squared_error"] = errors["error"] ** 2

    errors["error_type"] = np.select(
        [
            errors["error"] > 0,
            errors["error"] < 0,
        ],
        [
            "Underforecast",
            "Overforecast",
        ],
        default="Exact prediction",
    )

    errors["absolute_percentage_error"] = np.where(
        errors["actual_sales"].abs() > 0,
        errors["absolute_error"]
        / errors["actual_sales"].abs()
        * 100,
        np.nan,
    )

    # -----------------------------------------------------
    # 7. OVERALL SUMMARY
    # -----------------------------------------------------

    actual_total = errors["actual_sales"].sum()

    wape = (
        errors["absolute_error"].sum()
        / abs(actual_total)
        * 100
        if actual_total != 0
        else np.nan
    )

    summary = pd.DataFrame([{
        "model": "hist_gradient_boosting_extended_training",
        "training_start": TRAIN_START,
        "training_end": TRAIN_END,
        "test_start": TEST_START,
        "test_end": TEST_END,
        "test_records": len(errors),
        "MAE": mean_absolute_error(
            errors["actual_sales"],
            errors["predicted_sales"],
        ),
        "RMSE": np.sqrt(
            mean_squared_error(
                errors["actual_sales"],
                errors["predicted_sales"],
            )
        ),
        "WAPE_percent": wape,
        "underforecast_records": int(
            (errors["error_type"] == "Underforecast").sum()
        ),
        "overforecast_records": int(
            (errors["error_type"] == "Overforecast").sum()
        ),
        "exact_prediction_records": int(
            (errors["error_type"] == "Exact prediction").sum()
        ),
        "actual_sales_total": actual_total,
        "absolute_error_total": errors["absolute_error"].sum(),
    }])

    # -----------------------------------------------------
    # 8. DAILY ERROR SUMMARY
    # -----------------------------------------------------

    daily = (
        errors.groupby("dt", as_index=False)
        .agg(
            records=("actual_sales", "size"),
            actual_sales=("actual_sales", "sum"),
            predicted_sales=("predicted_sales", "sum"),
            absolute_error_total=("absolute_error", "sum"),
            MAE=("absolute_error", "mean"),
            RMSE=("squared_error", lambda x: np.sqrt(x.mean())),
            underforecast_records=(
                "error_type",
                lambda x: (x == "Underforecast").sum(),
            ),
            overforecast_records=(
                "error_type",
                lambda x: (x == "Overforecast").sum(),
            ),
        )
    )

    daily["WAPE_percent"] = np.where(
        daily["actual_sales"].abs() > 0,
        daily["absolute_error_total"]
        / daily["actual_sales"].abs()
        * 100,
        np.nan,
    )

    # -----------------------------------------------------
    # 9. SAVE REPORTS
    # -----------------------------------------------------

    errors.to_csv(ERRORS_FILE, index=False)
    summary.to_csv(SUMMARY_FILE, index=False)
    daily.to_csv(DAILY_FILE, index=False)

    print("\n" + "=" * 60)
    print("REGRESSION ERROR ANALYSIS")
    print("=" * 60)
    print(f"MAE: {summary.loc[0, 'MAE']:.6f}")
    print(f"RMSE: {summary.loc[0, 'RMSE']:.6f}")
    print(f"WAPE: {summary.loc[0, 'WAPE_percent']:.2f}%")
    print(
        "Underforecast records: "
        f"{summary.loc[0, 'underforecast_records']:,}"
    )
    print(
        "Overforecast records: "
        f"{summary.loc[0, 'overforecast_records']:,}"
    )

    print("\nReports saved:")
    print(ERRORS_FILE)
    print(SUMMARY_FILE)
    print(DAILY_FILE)
    print("\nOriginal source data was not modified.")


if __name__ == "__main__":
    main()
