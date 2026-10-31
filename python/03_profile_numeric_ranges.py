
from pathlib import Path

import pyarrow.parquet as pq


# ============================================================
# RETAIL DEMAND FORECASTING & INVENTORY INTELLIGENCE
# Numeric ranges and indicator profiling
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_DIR / "data" / "train.parquet"

NUMERIC_COLUMNS = [
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

INDICATOR_COLUMNS = [
    "holiday_flag",
    "activity_flag",
]


def main():
    print("=" * 65)
    print("RETAIL DEMAND FORECASTING & INVENTORY INTELLIGENCE")
    print("NUMERIC RANGES AND INDICATOR PROFILING")
    print("=" * 65)

    if not DATA_FILE.exists():
        print(f"ERROR: Dataset not found: {DATA_FILE}")
        return

    parquet_file = pq.ParquetFile(DATA_FILE)

    # Initialize statistics for each numeric column.
    stats = {
        column: {
            "count": 0,
            "minimum": float("inf"),
            "maximum": float("-inf"),
            "sum": 0.0,
        }
        for column in NUMERIC_COLUMNS
    }

    distinct_values = {
        column: set()
        for column in INDICATOR_COLUMNS
    }

    print(f"\nTotal rows: {parquet_file.metadata.num_rows:,}")
    print("\nScanning numeric columns...")

    for group_index in range(parquet_file.metadata.num_row_groups):
        table = parquet_file.read_row_group(
            group_index,
            columns=NUMERIC_COLUMNS,
        )

        for column in NUMERIC_COLUMNS:
            values = table.column(column).to_pylist()
            valid_values = [
                value for value in values
                if value is not None
            ]

            if valid_values:
                column_stats = stats[column]
                column_stats["count"] += len(valid_values)
                column_stats["minimum"] = min(
                    column_stats["minimum"],
                    min(valid_values),
                )
                column_stats["maximum"] = max(
                    column_stats["maximum"],
                    max(valid_values),
                )
                column_stats["sum"] += sum(valid_values)

        for column in INDICATOR_COLUMNS:
            values = table.column(column).to_pylist()
            distinct_values[column].update(
                value for value in values
                if value is not None
            )

        if (group_index + 1) % 500 == 0:
            print(
                f"Processed {group_index + 1:,} "
                f"of {parquet_file.metadata.num_row_groups:,} row groups"
            )

    print("\n" + "=" * 65)
    print("NUMERIC SUMMARY")
    print("=" * 65)

    for column, result in stats.items():
        count = result["count"]

        if count == 0:
            print(f"\n{column}: no valid values")
            continue

        average = result["sum"] / count

        print(f"\n{column}")
        print(f"Count: {count:,}")
        print(f"Minimum: {result['minimum']}")
        print(f"Maximum: {result['maximum']}")
        print(f"Mean: {average:.6f}")

    print("\n" + "=" * 65)
    print("INDICATOR DISTINCT VALUES")
    print("=" * 65)

    for column, values in distinct_values.items():
        print(f"\n{column}: {sorted(values)}")

    print("\n" + "=" * 65)
    print("PROFILE COMPLETED")
    print("The original Parquet file was not modified.")
    print("=" * 65)


if __name__ == "__main__":
    main()
