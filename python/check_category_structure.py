
import pandas as pd
from pathlib import Path

project_dir = Path(__file__).resolve().parent.parent
file_path = project_dir / "reports" / "17_category_demand_summary.csv"

df = pd.read_csv(file_path)

category_columns = [
    "first_category_id",
    "second_category_id",
    "third_category_id"
]

print("=" * 60)
print("CATEGORY STRUCTURE DIAGNOSTIC")
print("=" * 60)

print(f"\nTotal rows: {len(df):,}")

for col in category_columns:
    print(f"\n{col}")
    print(f"Distinct values: {df[col].nunique(dropna=True):,}")
    print(f"Missing values: {df[col].isna().sum():,}")

print("\n" + "=" * 60)
print("DUPLICATE COMBINATIONS")
print("=" * 60)

duplicates = df.duplicated(
    subset=category_columns,
    keep=False
)

print(f"Rows involved in duplicate combinations: {duplicates.sum():,}")

print("\nUnique combinations:")
print(df[category_columns].drop_duplicates().shape[0])

print("\n" + "=" * 60)
print("CATEGORY DISTRIBUTION")
print("=" * 60)

print(
    df.groupby("first_category_id", dropna=False)
      .size()
      .sort_values(ascending=False)
      .to_string()
)

print("\nDiagnostic completed.")
print("\n" + "=" * 60)
print("NORMALIZED DEMAND BY MAIN CATEGORY")
print("=" * 60)

category_demand = (
    df.groupby("first_category_id", as_index=False)
      .agg(
          normalized_demand_total=(
              "normalized_demand_total", "sum"
          ),
          subcategory_count=("third_category_id", "count")
      )
      .sort_values(
          "normalized_demand_total",
          ascending=False
      )
)

print(category_demand.to_string(index=False))
print(f"\nTotal main categories: {len(category_demand)}")
print(
    "\nDemand total:",
    round(category_demand["normalized_demand_total"].sum(), 3)
)