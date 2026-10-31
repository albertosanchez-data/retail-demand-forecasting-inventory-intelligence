
from pathlib import Path
from datetime import date
import pyarrow.parquet as pq


# ============================================================
# RETAIL DEMAND FORECASTING & INVENTORY INTELLIGENCE
# Step 06: Validate time-series continuity
# The original source data will not be modified.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "train.parquet"

KEY_COLUMNS = ["city_id", "store_id", "product_id"]
DATE_COLUMN = "dt"

print("=" * 70)
print("TIME-SERIES CONTINUITY VALIDATION")
print("=" * 70)
print(f"Source file: {DATA_FILE}")
print("Original source data will not be modified.")
print()

if not DATA_FILE.exists():
    raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

parquet_file = pq.ParquetFile(DATA_FILE)

# Each entry stores the first date, last date, and row count
# for one city-store-product series.
series_summary = {}

total_rows_processed = 0
total_row_groups = parquet_file.num_row_groups

for group_index in range(total_row_groups):
    table = parquet_file.read_row_group(
        group_index,
        columns=KEY_COLUMNS + [DATE_COLUMN]
    )

    cities = table.column("city_id").to_pylist()
    stores = table.column("store_id").to_pylist()
    products = table.column("product_id").to_pylist()
    dates = table.column(DATE_COLUMN).to_pylist()

    for city, store, product, date_text in zip(
        cities, stores, products, dates
    ):
        key = (city, store, product)

        if key not in series_summary:
            series_summary[key] = [
                date_text,
                date_text,
                1
            ]
        else:
            summary = series_summary[key]

            if date_text < summary[0]:
                summary[0] = date_text

            if date_text > summary[1]:
                summary[1] = date_text

            summary[2] += 1

    total_rows_processed += table.num_rows

    if (group_index + 1) % 500 == 0:
        print(
            f"Processed row groups: {group_index + 1:,}"
            f" / {total_row_groups:,}"
        )

print()
print("-" * 70)
print("PROCESSING SUMMARY")
print("-" * 70)
print(f"Rows processed: {total_rows_processed:,}")
print(f"Unique city-store-product series: {len(series_summary):,}")

# Analyze the observed date span of each series.
row_counts = []
series_with_possible_gaps = []
total_possible_missing_dates = 0
series_shorter_than_90_days = 0
series_exactly_90_days = 0
series_longer_than_90_days = 0

for key, summary in series_summary.items():
    first_date = date.fromisoformat(summary[0])
    last_date = date.fromisoformat(summary[1])
    observed_rows = summary[2]

    expected_days_in_span = (last_date - first_date).days + 1
    possible_missing_dates = expected_days_in_span - observed_rows

    row_counts.append(observed_rows)

    if possible_missing_dates > 0:
        series_with_possible_gaps.append(
            (
                key,
                summary[0],
                summary[1],
                observed_rows,
                expected_days_in_span,
                possible_missing_dates
            )
        )
        total_possible_missing_dates += possible_missing_dates

    if observed_rows < 90:
        series_shorter_than_90_days += 1
    elif observed_rows == 90:
        series_exactly_90_days += 1
    else:
        series_longer_than_90_days += 1

print()
print("-" * 70)
print("SERIES LENGTH SUMMARY")
print("-" * 70)
print(f"Shortest series (rows): {min(row_counts):,}")
print(f"Longest series (rows): {max(row_counts):,}")
print(f"Average rows per series: {sum(row_counts) / len(row_counts):.2f}")
print(f"Series with fewer than 90 rows: {series_shorter_than_90_days:,}")
print(f"Series with exactly 90 rows: {series_exactly_90_days:,}")
print(f"Series with more than 90 rows: {series_longer_than_90_days:,}")

print()
print("-" * 70)
print("POTENTIAL DATE GAPS")
print("-" * 70)
print(
    "Series with missing dates inside their observed date span: "
    f"{len(series_with_possible_gaps):,}"
)
print(
    "Potential missing dates across those series: "
    f"{total_possible_missing_dates:,}"
)

if series_with_possible_gaps:
    print()
    print("First 20 series with potential date gaps:")
    print(
        "city_id | store_id | product_id | first_date | last_date | "
        "rows | days_in_span | possible_gaps"
    )

    for item in series_with_possible_gaps[:20]:
        key, first_date, last_date, rows, span, gaps = item

        print(
            f"{key[0]} | {key[1]} | {key[2]} | "
            f"{first_date} | {last_date} | "
            f"{rows} | {span} | {gaps}"
        )
else:
    print("No date gaps were detected inside the observed spans.")

print()
print("=" * 70)
print("VALIDATION FINISHED")
print("No source data was modified.")
print("=" * 70)
