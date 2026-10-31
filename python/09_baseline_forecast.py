
"""
Retail Demand Forecasting & Inventory Intelligence
09_baseline_forecast.py

Baseline forecast:
- One series per city, store, and product.
- Training period: 2024-03-28 to 2024-06-11.
- Test period: 2024-06-12 to 2024-06-25 (14 days).
- Prediction: mean observed sales over the final 7 training days.
- Read-only access to PostgreSQL; no source data is modified.
"""

import os
import sys
from getpass import getpass
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from sklearn.metrics import mean_absolute_error, mean_squared_error


# ---------------------------------------------------------
# 1. Configuration
# ---------------------------------------------------------

DB_NAME = "retail_demand_db"
DB_USER = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

TABLE_NAME = "public.stg_retail_demand"

TRAIN_END = pd.Timestamp("2024-06-11")
TEST_START = pd.Timestamp("2024-06-12")
TEST_END = pd.Timestamp("2024-06-25")

LOOKBACK_DAYS = 7

PROJECT_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = PROJECT_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = REPORT_DIR / "09_baseline_forecast_metrics.csv"


def main():
    # -----------------------------------------------------
    # 2. Connect to PostgreSQL
    # -----------------------------------------------------

    print("=" * 65)
    print("RETAIL DEMAND FORECASTING & INVENTORY INTELLIGENCE")
    print("BASELINE FORECAST")
    print("=" * 65)

    password = os.environ.get("PGPASSWORD")

    if not password:
        password = getpass(
            "Enter the PostgreSQL password for user postgres: "
        )

    try:
        connection = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=password,
            host=DB_HOST,
            port=DB_PORT,
            connect_timeout=10,
            options="-c default_transaction_read_only=on",
        )
    except Exception as error:
        print("\nCould not connect to PostgreSQL.")
        print(f"Details: {error}")
        sys.exit(1)

    # -----------------------------------------------------
    # 3. Retrieve the training and test observations
    # -----------------------------------------------------

    query = """
        SELECT
            city_id,
            store_id,
            product_id,
            dt,
            sale_amount
        FROM public.stg_retail_demand
        WHERE dt BETWEEN %s AND %s
        ORDER BY city_id, store_id, product_id, dt;
    """

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    ("2024-06-05", "2024-06-25"),
                )
                rows = cursor.fetchall()
                column_names = [
                    description[0]
                    for description in cursor.description
                ]

        data = pd.DataFrame(rows, columns=column_names)

    except Exception as error:
        print("\nCould not retrieve the observations.")
        print(f"Details: {error}")
        connection.close()
        sys.exit(1)

    finally:
        if not connection.closed:
            connection.close()

    if data.empty:
        print("No observations were retrieved. Check the database.")
        sys.exit(1)

    data["dt"] = pd.to_datetime(data["dt"])

    print(f"\nRetrieved records: {len(data):,}")
    print(f"Training ends: {TRAIN_END.date()}")
    print(f"Test period: {TEST_START.date()} to {TEST_END.date()}")
    print(f"Lookback window: {LOOKBACK_DAYS} days")

    # -----------------------------------------------------
    # 4. Build forecasts using only training observations
    # -----------------------------------------------------

    training = data.loc[
        (data["dt"] >= pd.Timestamp("2024-06-05"))
        & (data["dt"] <= TRAIN_END)
    ].copy()

    test = data.loc[
        (data["dt"] >= TEST_START)
        & (data["dt"] <= TEST_END)
    ].copy()

    keys = ["city_id", "store_id", "product_id"]

    baseline = (
        training.groupby(keys, as_index=False)
        .agg(
            baseline_forecast=("sale_amount", "mean"),
            training_days=("dt", "nunique"),
        )
    )

    baseline = baseline.loc[
        baseline["training_days"] == LOOKBACK_DAYS
    ].copy()

    evaluation = test.merge(
        baseline[keys + ["baseline_forecast"]],
        on=keys,
        how="inner",
        validate="many_to_one",
    )

    if evaluation.empty:
        print("No matching series found for evaluation.")
        sys.exit(1)

    # -----------------------------------------------------
    # 5. Evaluate predictions
    # -----------------------------------------------------

    actual = evaluation["sale_amount"].astype(float).to_numpy()
    predicted = evaluation["baseline_forecast"].astype(float).to_numpy()

    mae = mean_absolute_error(actual, predicted)
    rmse = np.sqrt(mean_squared_error(actual, predicted))

    total_absolute_error = np.abs(actual - predicted).sum()
    total_actual = np.abs(actual).sum()

    wape = (
        total_absolute_error / total_actual * 100
        if total_actual != 0
        else np.nan
    )

    # -----------------------------------------------------
    # 6. Summarize evaluation coverage
    # -----------------------------------------------------

    test_series = test[keys].drop_duplicates().shape[0]
    forecast_series = baseline[keys].drop_duplicates().shape[0]
    evaluated_series = evaluation[keys].drop_duplicates().shape[0]

    metrics = pd.DataFrame(
        [
            {
                "model": "7_day_mean_baseline",
                "training_end": TRAIN_END.date(),
                "test_start": TEST_START.date(),
                "test_end": TEST_END.date(),
                "lookback_days": LOOKBACK_DAYS,
                "training_series": forecast_series,
                "test_series": test_series,
                "evaluated_series": evaluated_series,
                "test_records": len(test),
                "evaluated_records": len(evaluation),
                "MAE": mae,
                "RMSE": rmse,
                "WAPE_percent": wape,
            }
        ]
    )

    metrics.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    # -----------------------------------------------------
    # 7. Display results
    # -----------------------------------------------------

    print("\n" + "=" * 65)
    print("BASELINE EVALUATION RESULTS")
    print("=" * 65)

    print(f"Test records:       {len(test):,}")
    print(f"Evaluated records:  {len(evaluation):,}")
    print(f"Test series:        {test_series:,}")
    print(f"Forecastable series:{forecast_series:>10,}")
    print(f"Evaluated series:   {evaluated_series:,}")
    print(f"MAE:                {mae:.6f}")
    print(f"RMSE:               {rmse:.6f}")
    print(f"WAPE:               {wape:.2f}%")

    print("\nMetrics saved to:")
    print(OUTPUT_FILE)

    print("\nNote: sale_amount is normalized observed sales,")
    print("not necessarily unconstrained customer demand.")


if __name__ == "__main__":
    main()
