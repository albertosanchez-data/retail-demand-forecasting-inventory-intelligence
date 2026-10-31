
from pathlib import Path
import gc

import pandas as pd
import pyarrow.parquet as pq


# ============================================================
# RETAIL DEMAND FORECASTING & INVENTORY INTELLIGENCE
# Power BI Aggregated Datasets
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
SOURCE_FILE = PROJECT_DIR / "data" / "train.parquet"
OUTPUT_DIR = PROJECT_DIR / "reports"

BATCH_SIZE = 250_000

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
    "stock_hour6_22_cnt",
    "discount",
    "holiday_flag",
    "activity_flag",
]

GROUPS = {
    "daily": ["dt"],

    "product": [
        "product_id",
        "first_category_id",
        "second_category_id",
        "third_category_id",
    ],

    "store": [
        "city_id",
        "store_id",
        "management_group_id",
    ],

    "category": [
        "first_category_id",
        "second_category_id",
        "third_category_id",
    ],

    "drivers": [
        "holiday_flag",
        "activity_flag",
        "discount_band",
    ],
}

OUTPUT_FILES = {
    "daily": "14_daily_demand_summary.csv",
    "product": "15_product_demand_summary.csv",
    "store": "16_store_demand_summary.csv",
    "category": "17_category_demand_summary.csv",
    "drivers": "18_demand_driver_summary.csv",
}


# ============================================================
# BATCH AGGREGATION
# ============================================================

def aggregate_batch(df, group_columns):

    return (
        df.groupby(
            group_columns,
            dropna=False,
            observed=True
        )
        .agg(
            normalized_demand_total=("sale_amount", "sum"),
            observation_count=("sale_amount", "count"),
            stock_hours_sum=("stock_hour6_22_cnt", "sum"),
        )
        .reset_index()
    )


# ============================================================
# FINAL CONSOLIDATION
# ============================================================

def consolidate_partials(partials, group_columns):

    if not partials:
        raise ValueError(
            f"No partial results available for {group_columns}"
        )

    combined = pd.concat(
        partials,
        ignore_index=True
    )

    result = (
        combined.groupby(
            group_columns,
            dropna=False,
            observed=True
        )
        .agg(
            normalized_demand_total=(
                "normalized_demand_total", "sum"
            ),
            observation_count=(
                "observation_count", "sum"
            ),
            stock_hours_sum=(
                "stock_hours_sum", "sum"
            ),
        )
        .reset_index()
    )

    result["average_normalized_demand_per_observation"] = (
        result["normalized_demand_total"]
        / result["observation_count"]
    )

    result["average_stock_hours_6_22"] = (
        result["stock_hours_sum"]
        / result["observation_count"]
    )

    result = result.drop(
        columns=["stock_hours_sum"]
    )

    result = result.sort_values(
        "normalized_demand_total",
        ascending=False
    ).reset_index(drop=True)

    return result


# ============================================================
# MAIN PROCESS
# ============================================================

def main():

    print("=" * 65)
    print("POWER BI AGGREGATION PROCESS")
    print("=" * 65)

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {SOURCE_FILE}"
        )

    parquet_file = pq.ParquetFile(SOURCE_FILE)

    total_rows = parquet_file.metadata.num_rows

    print(f"Source rows: {total_rows:,}")
    print(f"Row groups: {parquet_file.num_row_groups:,}")
    print()

    partial_results = {
        name: [] for name in GROUPS
    }

    batch_number = 0
    processed_rows = 0

    # --------------------------------------------------------
    # READ SOURCE IN BATCHES
    # --------------------------------------------------------

    for batch in parquet_file.iter_batches(
        batch_size=BATCH_SIZE,
        columns=COLUMNS
    ):

        batch_number += 1

        df = batch.to_pandas()
        processed_rows += len(df)

        df["discount_band"] = pd.cut(
            df["discount"],
            bins=[
                float("-inf"),
                0,
                0.10,
                0.25,
                0.50,
                0.75,
                1.00,
                float("inf"),
            ],
            labels=[
                "No discount",
                "0-10%",
                "10-25%",
                "25-50%",
                "50-75%",
                "75-100%",
                "Above 100%",
            ],
            include_lowest=True,
            right=True,
        ).astype("string")

        for name, group_columns in GROUPS.items():

            partial = aggregate_batch(
                df,
                group_columns
            )

            partial_results[name].append(partial)

        print(
            f"Processed batch {batch_number}: "
            f"{len(df):,} rows "
            f"({processed_rows:,}/{total_rows:,})"
        )

        del df
        gc.collect()

    if processed_rows != total_rows:
        raise RuntimeError(
            f"Processed {processed_rows:,} rows, "
            f"but expected {total_rows:,}."
        )

    print()
    print("All source rows processed successfully.")
    print()
    print("Creating final aggregated reports...")
    print()

    # --------------------------------------------------------
    # CREATE CSV REPORTS
    # --------------------------------------------------------

    for name, group_columns in GROUPS.items():

        result = consolidate_partials(
            partial_results[name],
            group_columns
        )

        output_file = OUTPUT_DIR / OUTPUT_FILES[name]

        result.to_csv(
            output_file,
            index=False,
            encoding="utf-8-sig",
            float_format="%.6f"
        )

        print(
            f"Created: {output_file.name} | "
            f"{len(result):,} rows"
        )

        del result
        del partial_results[name]
        gc.collect()

    print()
    print("=" * 65)
    print("AGGREGATION COMPLETED SUCCESSFULLY")
    print(f"Rows processed: {processed_rows:,}")
    print("Original Parquet file was not modified.")
    print("=" * 65)


if __name__ == "__main__":
    main()
