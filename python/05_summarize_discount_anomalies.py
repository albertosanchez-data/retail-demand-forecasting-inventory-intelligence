
from pathlib import Path
from collections import Counter

import pyarrow.parquet as pq


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_DIR / "data" / "train.parquet"

COLUMNS = [
    "city_id",
    "store_id",
    "product_id",
    "dt",
    "discount",
]


def main():
    print("=" * 65)
    print("DISCOUNT ANOMALIES: FULL SUMMARY")
    print("=" * 65)

    if not DATA_FILE.exists():
        print(f"ERROR: Dataset not found: {DATA_FILE}")
        return

    parquet_file = pq.ParquetFile(DATA_FILE)

    records = []
    product_counts = Counter()
    city_counts = Counter()
    store_counts = Counter()
    discount_counts = Counter()

    for group_index in range(parquet_file.metadata.num_row_groups):
        table = parquet_file.read_row_group(
            group_index,
            columns=COLUMNS,
        )

        columns = {
            name: table.column(name).to_pylist()
            for name in COLUMNS
        }

        for city, store, product, date, discount in zip(
            columns["city_id"],
            columns["store_id"],
            columns["product_id"],
            columns["dt"],
            columns["discount"],
        ):
            if discount is not None and discount > 1:
                records.append(
                    (city, store, product, date, discount)
                )
                product_counts[product] += 1
                city_counts[city] += 1
                store_counts[store] += 1
                discount_counts[discount] += 1

    print(f"\nTotal anomalous records: {len(records)}")
    print(f"Distinct products: {len(product_counts)}")
    print(f"Distinct cities: {len(city_counts)}")
    print(f"Distinct stores: {len(store_counts)}")
    print(f"Distinct discount values: {len(discount_counts)}")

    print("\nRECORDS BY PRODUCT")
    for product, count in sorted(product_counts.items()):
        print(f"Product {product}: {count} records")

    print("\nRECORDS BY CITY")
    for city, count in sorted(city_counts.items()):
        print(f"City {city}: {count} records")

    print("\nRECORDS BY STORE")
    for store, count in sorted(store_counts.items()):
        print(f"Store {store}: {count} records")

    print("\nALL RECORDS WITH DISCOUNT > 1")
    print("city_id | store_id | product_id | dt | discount")

    for record in sorted(records, key=lambda row: (row[2], row[0], row[1], row[3])):
        print(" | ".join(str(value) for value in record))

    print("\nNo source data was modified.")
    print("Investigation completed.")


if __name__ == "__main__":
    main()
