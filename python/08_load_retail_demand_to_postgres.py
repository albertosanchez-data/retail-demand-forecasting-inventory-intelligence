
from pathlib import Path
from getpass import getpass

import math
import pyarrow.parquet as pq
import psycopg2
from psycopg2.extras import execute_values


# ============================================================
# 1. CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = PROJECT_DIR / "data" / "train.parquet"

BATCH_SIZE = 10_000
INSERT_PAGE_SIZE = 1_000

TABLE_NAME = "public.stg_retail_demand"

COLUMNS = [
    "city_id",
    "store_id",
    "management_group_id",
    "first_category_id",
    "second_category_id",
    "third_category_id",
    "product_id",
    "dt",
    "sale_amount",
    "hours_sale",
    "stock_hour6_22_cnt",
    "hours_stock_status",
    "discount",
    "holiday_flag",
    "activity_flag",
    "precpt",
    "avg_temperature",
    "avg_humidity",
    "avg_wind_level",
]

INSERT_SQL = """
    INSERT INTO public.stg_retail_demand (
        city_id,
        store_id,
        management_group_id,
        first_category_id,
        second_category_id,
        third_category_id,
        product_id,
        dt,
        sale_amount,
        hours_sale,
        stock_hour6_22_cnt,
        hours_stock_status,
        discount,
        holiday_flag,
        activity_flag,
        precpt,
        avg_temperature,
        avg_humidity,
        avg_wind_level
    )
    VALUES %s
    ON CONFLICT (city_id, store_id, product_id, dt)
    DO NOTHING
"""


# ============================================================
# 2. CONVERT SOURCE VALUES
# ============================================================

def convert_value(value):
    """Convert Arrow/NumPy values to PostgreSQL-compatible values."""

    if hasattr(value, "tolist"):
        value = value.tolist()

    if isinstance(value, list):
        return [convert_value(item) for item in value]

    if hasattr(value, "item"):
        value = value.item()

    if value is None:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    return value


# ============================================================
# 3. VALIDATE EACH BATCH
# ============================================================

def prepare_records(batch):
    records = []

    for row_number, row in enumerate(
        batch.to_pydict().values()
    ):
        # This loop is not used for row conversion.
        # Actual records are constructed below.
        break

    data = batch.to_pydict()
    row_count = batch.num_rows

    for i in range(row_count):
        record = tuple(
            convert_value(data[column][i])
            for column in COLUMNS
        )

        if any(value is None for value in record):
            raise ValueError(
                f"Null value found in batch row {i + 1}. "
                "The source batch was not inserted."
            )

        if len(record[9]) != 24:
            raise ValueError(
                f"Row {i + 1}: hours_sale does not have 24 values."
            )

        if len(record[11]) != 24:
            raise ValueError(
                f"Row {i + 1}: hours_stock_status "
                "does not have 24 values."
            )

        records.append(record)

    return records


# ============================================================
# 4. MAIN LOAD PROCESS
# ============================================================

def main():
    print("=" * 70)
    print("RETAIL DEMAND FORECASTING & INVENTORY INTELLIGENCE")
    print("BATCH LOAD TO POSTGRESQL")
    print("=" * 70)

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Parquet file not found: {DATA_FILE}"
        )

    parquet_file = pq.ParquetFile(DATA_FILE)
    expected_rows = parquet_file.metadata.num_rows
    source_columns = parquet_file.schema_arrow.names

    missing_columns = [
        column for column in COLUMNS
        if column not in source_columns
    ]

    if missing_columns:
        raise ValueError(
            f"Required columns missing from source: {missing_columns}"
        )

    print(f"\nSource: {DATA_FILE}")
    print(f"Expected source rows: {expected_rows:,}")
    print(f"Batch size: {BATCH_SIZE:,}")

    password = getpass("\nEnter PostgreSQL password: ")

    conn = None

    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="retail_demand_db",
            user="postgres",
            password=password,
            connect_timeout=10,
        )

        conn.autocommit = False

        with conn.cursor() as cur:
            cur.execute(
                "SELECT current_database(), current_user;"
            )
            database_name, username = cur.fetchone()

            if database_name != "retail_demand_db":
                raise RuntimeError(
                    f"Unexpected database: {database_name}"
                )

            print(f"\nConnected database: {database_name}")
            print(f"Connected user: {username}")

            cur.execute(
                "SELECT COUNT(*) FROM public.stg_retail_demand;"
            )
            existing_rows = cur.fetchone()[0]

        conn.commit()

        if existing_rows > expected_rows:
            raise RuntimeError(
                f"Destination has {existing_rows:,} rows, more than "
                f"the source ({expected_rows:,}). Load stopped."
            )

        if existing_rows == expected_rows:
            print(
                "\nThe destination already contains the expected "
                "number of rows."
            )
            print("No rows will be inserted.")

        else:
            if existing_rows == 0:
                print("\nDestination table is empty.")
                required_word = "LOAD"
                prompt = (
                    "To begin the full load, type LOAD: "
                )
            else:
                print(
                    f"\nExisting rows: {existing_rows:,}. "
                    "This may be a previous partial load."
                )
                print(
                    "The script can resume, skipping keys already "
                    "present in the destination."
                )
                required_word = "RESUME"
                prompt = (
                    "To resume the load, type RESUME: "
                )

            confirmation = input(prompt).strip()

            if confirmation != required_word:
                print("\nLoad cancelled. No new rows were inserted.")
                return

            processed_rows = 0

            for batch in parquet_file.iter_batches(
                batch_size=BATCH_SIZE,
                columns=COLUMNS,
            ):
                records = prepare_records(batch)

                with conn.cursor() as cur:
                    execute_values(
                        cur,
                        INSERT_SQL,
                        records,
                        page_size=INSERT_PAGE_SIZE,
                    )

                # Commit each batch. If a later batch fails,
                # already committed batches remain available
                # for a subsequent RESUME run.
                conn.commit()

                processed_rows += batch.num_rows

                print(
                    f"Source processed: "
                    f"{processed_rows:,} / {expected_rows:,} "
                    f"({processed_rows / expected_rows:.1%})"
                )

        # ====================================================
        # 5. FINAL VALIDATION
        # ====================================================

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*),
                    COUNT(DISTINCT
                        (city_id, store_id, product_id, dt)
                    ),
                    MIN(dt),
                    MAX(dt),
                    MIN(cardinality(hours_sale)),
                    MAX(cardinality(hours_sale)),
                    MIN(cardinality(hours_stock_status)),
                    MAX(cardinality(hours_stock_status))
                FROM public.stg_retail_demand;
                """
            )

            (
                total_rows,
                distinct_keys,
                min_date,
                max_date,
                min_sale_hours,
                max_sale_hours,
                min_stock_hours,
                max_stock_hours,
            ) = cur.fetchone()

        conn.commit()

        print("\n" + "=" * 70)
        print("FINAL VALIDATION")
        print("=" * 70)
        print(f"Expected source rows: {expected_rows:,}")
        print(f"Rows in destination: {total_rows:,}")
        print(f"Distinct business keys: {distinct_keys:,}")
        print(f"Date range: {min_date} to {max_date}")
        print(
            "hours_sale array lengths: "
            f"{min_sale_hours} to {max_sale_hours}"
        )
        print(
            "hours_stock_status array lengths: "
            f"{min_stock_hours} to {max_stock_hours}"
        )

        if total_rows != expected_rows:
            raise RuntimeError(
                "Row-count mismatch. Do not consider the load complete. "
                "Check the source and destination before continuing."
            )

        if distinct_keys != total_rows:
            raise RuntimeError(
                "Business-key validation failed."
            )

        if (
            min_sale_hours != 24
            or max_sale_hours != 24
            or min_stock_hours != 24
            or max_stock_hours != 24
        ):
            raise RuntimeError(
                "Hourly-array validation failed."
            )

        print("\nLOAD AND VALIDATION: SUCCESS")

    except Exception:
        if conn is not None:
            conn.rollback()

        print(
            "\nERROR: The process stopped. Previously committed "
            "batches may remain in the table."
        )
        raise

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
