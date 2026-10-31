
"""
Retail Demand Forecasting & Inventory Intelligence
10_weekly_seasonal_forecast.py

Weekly seasonal forecast:
- One series per city, store, and product.
- Reference pattern: June 5 to June 11, 2024.
- Test period: June 12 to June 25, 2024.
- Forecast repeats the corresponding weekday from the reference week.
- PostgreSQL connection is read-only.
"""

import os
import sys
from getpass import getpass
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from sklearn.metrics import mean_absolute_error, mean_squared_error


DB_NAME = "retail_demand_db"
DB_USER = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

REFERENCE_START = pd.Timestamp("2024-06-05")
REFERENCE_END = pd.Timestamp("2024-06-11")
TEST_START = pd.Timestamp("2024-06-12")
TEST_END = pd.Timestamp("2024-06-25")

PROJECT_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = PROJECT_DIR / "reports"
OUTPUT_FILE = REPORT_DIR / "10_weekly_seasonal_forecast_metrics.csv"


def main():
    print("=" * 65)
    print("RETAIL DEMAND FORECASTING & INVENTORY INTELLIGENCE")
    print("WEEKLY SEASONAL FORECAST")
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
                columns = [
                    description[0]
                    for description in cursor.description
                ]

        data = pd.DataFrame(rows, columns=columns)

    except Exception as error:
        print("\nCould not retrieve observations.")
        print(f"Details: {error}")
        sys.exit(1)

    finally:
        if not connection.closed:
            connection.close()

    if data.empty:
        print("No observations were retrieved.")
        sys.exit(1)

    data["dt"] = pd.to_datetime(data["dt"])

    keys = ["city_id", "store_id", "product_id"]

    reference = data.loc[
        data["dt"].between(REFERENCE_START, REFERENCE_END)
    ].copy()

    test = data.loc[
        data["dt"].between(TEST_START, TEST_END)
    ].copy()

    # Each series must have all seven reference dates.
    reference_counts = (
        reference.groupby(keys)["dt"]
        .nunique()
        .rename("reference_days")
        .reset_index()
    )

    valid_series = reference_counts.loc[
        reference_counts["reference_days"] == 7, keys
    ]

    reference = reference.merge(
        valid_series,
        on=keys,
        how="inner",
        validate="many_to_one",
    )

    # Use weekday as the seasonal position:
    # Wednesday's reference sales forecast the next Wednesday, etc.
    reference["weekday"] = reference["dt"].dt.dayofweek

    seasonal_pattern = reference[
        keys + ["weekday", "sale_amount"]
    ].rename(
        columns={"sale_amount": "forecast"}
    )

    test["weekday"] = test["dt"].dt.dayofweek

    evaluation = test.merge(
        seasonal_pattern,
        on=keys + ["weekday"],
        how="inner",
        validate="many_to_one",
    )

    if evaluation.empty:
        print("No observations could be evaluated.")
        sys.exit(1)

    actual = evaluation["sale_amount"].astype(float).to_numpy()
    predicted = evaluation["forecast"].astype(float).to_numpy()

    mae = mean_absolute_error(actual, predicted)
    rmse = np.sqrt(mean_squared_error(actual, predicted))

    total_absolute_error = np.abs(actual - predicted).sum()
    total_actual = np.abs(actual).sum()

    wape = (
        total_absolute_error / total_actual * 100
        if total_actual != 0
        else np.nan
    )

    test_series = test[keys].drop_duplicates().shape[0]
    forecast_series = valid_series.shape[0]
    evaluated_series = evaluation[keys].drop_duplicates().shape[0]

    metrics = pd.DataFrame(
        [
            {
                "model": "weekly_seasonal_naive",
                "reference_start": REFERENCE_START.date(),
                "reference_end": REFERENCE_END.date(),
                "test_start": TEST_START.date(),
                "test_end": TEST_END.date(),
                "training_days": 7,
                "forecastable_series": forecast_series,
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

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 65)
    print("WEEKLY SEASONAL EVALUATION RESULTS")
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
