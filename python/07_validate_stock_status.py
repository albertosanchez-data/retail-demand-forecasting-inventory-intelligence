
from pathlib import Path
from collections import Counter

import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "train.parquet"

print("=" * 70)
print("STOCK STATUS VALIDATION - CORRECTED HOUR WINDOW")
print("=" * 70)
print("Source data will not be modified.")
print()

if not DATA_FILE.exists():
    raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

parquet_file = pq.ParquetFile(DATA_FILE)

total_rows = 0
list_lengths = Counter()
status_values = Counter()
invalid_values = Counter()

zero_convention_mismatches = 0
one_convention_mismatches = 0
neither_convention_mismatches = 0

daily_count_distribution = Counter()
examples = []

for group_index in range(parquet_file.num_row_groups):
    table = parquet_file.read_row_group(
        group_index,
        columns=["stock_hour6_22_cnt", "hours_stock_status"]
    )

    daily_counts = table.column("stock_hour6_22_cnt").to_pylist()
    hourly_vectors = table.column("hours_stock_status").to_pylist()

    for daily_count, statuses in zip(daily_counts, hourly_vectors):
        total_rows += 1
        daily_count_distribution[daily_count] += 1

        if statuses is None:
            list_lengths["null"] += 1
            continue

        list_lengths[len(statuses)] += 1

        for value in statuses:
            status_values[value] += 1
            if value not in (0, 1):
                invalid_values[value] += 1

        if len(statuses) != 24:
            continue

        # Provisional assumption:
        # index 0 = 00:00, index 1 = 01:00, etc.
        # Positions 6 through 21 represent 06:00-21:00.
        operating_hours = statuses[6:22]

        zeros = sum(value == 0 for value in operating_hours)
        ones = sum(value == 1 for value in operating_hours)

        if zeros != daily_count:
            zero_convention_mismatches += 1

        if ones != daily_count:
            one_convention_mismatches += 1

        if zeros != daily_count and ones != daily_count:
            neither_convention_mismatches += 1

            if len(examples) < 10:
                examples.append({
                    "daily_count": daily_count,
                    "hours_06_to_21": operating_hours,
                    "zeros": zeros,
                    "ones": ones
                })

    if (group_index + 1) % 500 == 0:
        print(
            f"Processed row groups: {group_index + 1:,}"
            f" / {parquet_file.num_row_groups:,}"
        )

print()
print("-" * 70)
print("BASIC VALIDATION")
print("-" * 70)
print(f"Rows processed: {total_rows:,}")
print(f"Hourly vector lengths: {dict(list_lengths)}")
print(f"Hourly status values: {dict(status_values)}")
print(f"Values outside 0 and 1: {dict(invalid_values)}")

print()
print("-" * 70)
print("DAILY COUNT COMPARISON: HOURS 06:00-21:00")
print("-" * 70)
print(
    "Rows where zero-count differs from daily count: "
    f"{zero_convention_mismatches:,}"
)
print(
    "Rows where one-count differs from daily count: "
    f"{one_convention_mismatches:,}"
)
print(
    "Rows where neither count matches: "
    f"{neither_convention_mismatches:,}"
)

print()
print("Daily count frequency:")
for value in range(17):
    print(f"{value:>2}: {daily_count_distribution.get(value, 0):,}")

if examples:
    print()
    print("First examples where neither count matches:")
    for example in examples:
        print(example)

print()
print("=" * 70)
print("VALIDATION FINISHED")
print("Hourly alignment and status encoding remain to be confirmed.")
print("No source data was modified.")
print("=" * 70)
