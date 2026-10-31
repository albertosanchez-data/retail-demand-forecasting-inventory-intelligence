
from pathlib import Path

import pyarrow.parquet as pq


# ============================================================
# RETAIL DEMAND FORECASTING & INVENTORY INTELLIGENCE
# Complete initial data quality profile
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_DIR / "data" / "train.parquet"

KEY_COLUMNS = [
    "city_id",
    "store_id",
    "product_id",
    "dt",
]


def main():
    print("=" * 65)
    print("RETAIL DEMAND FORECASTING & INVENTORY INTELLIGENCE")
    print("COMPLETE INITIAL DATA QUALITY PROFILE")
    print("=" * 65)

    if not DATA_FILE.exists():
        print(f"ERROR: Dataset not found: {DATA_FILE}")
        return

    parquet_file = pq.ParquetFile(DATA_FILE)
    metadata = parquet_file.metadata

    all_columns = parquet_file.schema_arrow.names

    print(f"\nFile: {DATA_FILE.name}")
    print(f"Total rows: {metadata.num_rows:,}")
    print(f"Total columns: {metadata.num_columns}")
    print(f"Row groups: {metadata.num_row_groups:,}")

    # Count nulls in every column.
    null_counts = {column: 0 for column in all_columns}

    min_date = None
    max_date = None

    # Track unique business keys across all row groups.
    seen_keys = set()
    duplicate_key_count = 0
    total_rows_scanned = 0

    print("\nScanning all columns and checking business keys...")

    for group_index in range(metadata.num_row_groups):
        table = parquet_file.read_row_group(group_index)

        total_rows_scanned += table.num_rows

        for column in all_columns:
            null_counts[column] += table.column(column).null_count

        dates = table.column("dt").to_pylist()
        valid_dates = [value for value in dates if value is not None]

        if valid_dates:
            group_min = min(valid_dates)
            group_max = max(valid_dates)

            if min_date is None or group_min < min_date:
                min_date = group_min

            if max_date is None or group_max > max_date:
                max_date = group_max

        keys_table = table.select(KEY_COLUMNS)

        for key in zip(
            keys_table.column("city_id").to_pylist(),
            keys_table.column("store_id").to_pylist(),
            keys_table.column("product_id").to_pylist(),
            keys_table.column("dt").to_pylist(),
        ):
            if key in seen_keys:
                duplicate_key_count += 1
            else:
                seen_keys.add(key)

        if (group_index + 1) % 500 == 0:
            print(
                f"Processed {group_index + 1:,} "
                f"of {metadata.num_row_groups:,} row groups"
            )

    print("\n" + "=" * 65)
    print("PROFILE RESULTS")
    print("=" * 65)

    print(f"\nRows scanned: {total_rows_scanned:,}")
    print(f"Minimum date: {min_date}")
    print(f"Maximum date: {max_date}")

    print("\nNULL VALUES BY COLUMN")

    for column, count in null_counts.items():
        percentage = (
            count / total_rows_scanned * 100
            if total_rows_scanned > 0
            else 0
        )
        print(f"{column}: {count:,} ({percentage:.4f}%)")

    total_nulls = sum(null_counts.values())

    print(f"\nTotal null cells: {total_nulls:,}")

    print("\nDUPLICATE BUSINESS KEYS")
    print(f"Key: {', '.join(KEY_COLUMNS)}")
    print(f"Duplicate rows detected: {duplicate_key_count:,}")

    print("\n" + "=" * 65)
    print("PROFILE COMPLETED")
    print("The original Parquet file was not modified.")
    print("=" * 65)


if __name__ == "__main__":
    main()
