
from pathlib import Path

import pyarrow.parquet as pq


# ============================================================
# RETAIL DEMAND FORECASTING & INVENTORY INTELLIGENCE
# Hourly data validation
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_DIR / "data" / "train.parquet"

LIST_COLUMNS = [
    "hours_sale",
    "hours_stock_status",
]

CHECK_COLUMNS = [
    "sale_amount",
    "stock_hour6_22_cnt",
    "discount",
    "holiday_flag",
    "activity_flag",
    "precpt",
    "avg_temperature",
    "avg_humidity",
    "avg_wind_level",
]


def main():
    print("=" * 65)
    print("RETAIL DEMAND FORECASTING & INVENTORY INTELLIGENCE")
    print("HOURLY DATA VALIDATION")
    print("=" * 65)

    if not DATA_FILE.exists():
        print(f"ERROR: Dataset not found: {DATA_FILE}")
        return

    parquet_file = pq.ParquetFile(DATA_FILE)
    total_rows = parquet_file.metadata.num_rows

    list_counts = {
        column: {
            "rows_checked": 0,
            "wrong_length": 0,
            "empty_lists": 0,
            "null_lists": 0,
            "null_elements": 0,
        }
        for column in LIST_COLUMNS
    }

    numeric_counts = {
        column: {
            "nulls": 0,
            "negative": 0,
        }
        for column in CHECK_COLUMNS
    }

    print(f"\nFile: {DATA_FILE.name}")
    print(f"Total rows: {total_rows:,}")
    print("\nScanning records...")

    for group_index in range(parquet_file.metadata.num_row_groups):
        table = parquet_file.read_row_group(
            group_index,
            columns=LIST_COLUMNS + CHECK_COLUMNS,
        )

        # Validate hourly lists.
        for column in LIST_COLUMNS:
            values = table.column(column).to_pylist()

            for value in values:
                list_counts[column]["rows_checked"] += 1

                if value is None:
                    list_counts[column]["null_lists"] += 1
                elif len(value) == 0:
                    list_counts[column]["empty_lists"] += 1
                elif len(value) != 24:
                    list_counts[column]["wrong_length"] += 1

                if value is not None:
                    list_counts[column]["null_elements"] += sum(
                        element is None for element in value
                    )

        # Basic checks for selected numeric columns.
        for column in CHECK_COLUMNS:
            values = table.column(column).to_pylist()
            numeric_counts[column]["nulls"] += sum(
                value is None for value in values
            )
            numeric_counts[column]["negative"] += sum(
                value is not None and value < 0
                for value in values
            )

        if (group_index + 1) % 500 == 0:
            print(
                f"Processed {group_index + 1:,} "
                f"of {parquet_file.metadata.num_row_groups:,} row groups"
            )

    print("\n" + "=" * 65)
    print("HOURLY LIST VALIDATION")
    print("=" * 65)

    for column, counts in list_counts.items():
        print(f"\n{column}")
        for name, count in counts.items():
            print(f"{name}: {count:,}")

    print("\n" + "=" * 65)
    print("NUMERIC VALUE CHECKS")
    print("=" * 65)

    for column, counts in numeric_counts.items():
        print(f"\n{column}")
        print(f"Null values: {counts['nulls']:,}")
        print(f"Negative values: {counts['negative']:,}")

    print("\n" + "=" * 65)
    print("VALIDATION COMPLETED")
    print("The original Parquet file was not modified.")
    print("=" * 65)


if __name__ == "__main__":
    main()
