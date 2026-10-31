
from pathlib import Path
from collections import Counter

import pyarrow.parquet as pq


# ============================================================
# RETAIL DEMAND FORECASTING & INVENTORY INTELLIGENCE
# Investigate discount values above 1
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_DIR / "data" / "train.parquet"

KEY_COLUMNS = [
    "city_id",
    "store_id",
    "product_id",
    "dt",
]

CHECK_COLUMNS = KEY_COLUMNS + [
    "discount",
]


def main():
    print("=" * 65)
    print("RETAIL DEMAND FORECASTING & INVENTORY INTELLIGENCE")
    print("DISCOUNT VALUES ABOVE 1: INVESTIGATION")
    print("=" * 65)

    if not DATA_FILE.exists():
        print(f"ERROR: Dataset not found: {DATA_FILE}")
        return

    parquet_file = pq.ParquetFile(DATA_FILE)

    rows_above_one = 0
    discount_counts = Counter()
    sample_rows = []

    print(f"\nTotal rows: {parquet_file.metadata.num_rows:,}")
    print("Condition being investigated: discount > 1")
    print("\nScanning records...")

    for group_index in range(parquet_file.metadata.num_row_groups):
        table = parquet_file.read_row_group(
            group_index,
            columns=CHECK_COLUMNS,
        )

        discounts = table.column("discount").to_pylist()
        cities = table.column("city_id").to_pylist()
        stores = table.column("store_id").to_pylist()
        products = table.column("product_id").to_pylist()
        dates = table.column("dt").to_pylist()

        for city, store, product, date, discount in zip(
            cities,
            stores,
            products,
            dates,
            discounts,
        ):
            if discount is not None and discount > 1:
                rows_above_one += 1
                discount_counts[discount] += 1

                if len(sample_rows) < 20:
                    sample_rows.append(
                        (city, store, product, date, discount)
                    )

        if (group_index + 1) % 500 == 0:
            print(
                f"Processed {group_index + 1:,} "
                f"of {parquet_file.metadata.num_row_groups:,} row groups"
            )

    total_rows = parquet_file.metadata.num_rows
    percentage = rows_above_one / total_rows * 100

    print("\n" + "=" * 65)
    print("INVESTIGATION RESULTS")
    print("=" * 65)

    print(f"\nRows with discount > 1: {rows_above_one:,}")
    print(f"Percentage of all rows: {percentage:.6f}%")

    print("\nDistinct discount values above 1:")

    if discount_counts:
        for value, count in sorted(discount_counts.items()):
            print(f"{value}: {count:,} rows")
    else:
        print("None found.")

    print("\nSAMPLE RECORDS (maximum 20)")

    if sample_rows:
        print("city_id | store_id | product_id | dt | discount")
        for row in sample_rows:
            print(" | ".join(str(value) for value in row))
    else:
        print("No records to display.")

    print("\n" + "=" * 65)
    print("INVESTIGATION COMPLETED")
    print("No source data was modified.")
    print("=" * 65)


if __name__ == "__main__":
    main()
