# Data Quality Findings

## Project

Retail Demand Forecasting & Inventory Intelligence

## Source dataset

FreshRetailNet-50K — train.parquet

## 1. Initial data profiling

- Total records: 4,500,000
- Total columns: 19
- Date range: 2024-03-28 to 2024-06-25
- Null values in all 19 columns: 0
- Duplicate business keys detected: 0

Business key:
city_id + store_id + product_id + dt

## 2. Hourly data validation

- hours_sale: all 4,500,000 records contain 24 elements.
- hours_stock_status: all 4,500,000 records contain 24 elements.
- Null lists, empty lists, and null list elements: 0.
- Negative values in the nine selected numeric columns: 0.

## 3. Discount anomaly investigation

Documented rule from the dataset documentation:

- discount = 1.0 represents no discount.
- discount = 0.9 represents a 10% discount.

Observed findings:

- Records with discount > 1: 34.
- Percentage of the dataset: approximately 0.000756%.
- Distinct products involved: 1.
- Product ID: 37.
- Distinct cities involved: 2.
- Distinct stores involved: 6.
- City 11: 32 records.
- City 15: 2 records.
- Most frequent value: 1.088, appearing 18 times.
- Highest observed value: 1.088.

Store distribution:

- Store 293: 5 records.
- Store 326: 6 records.
- Store 529: 6 records.
- Store 608: 10 records.
- Store 611: 2 records.
- Store 614: 5 records.

## 4. Interpretation and limitations

Values above 1 do not match the documented examples for the
discount variable and require further investigation.

The observed concentration in product 37 does not establish
the cause of these values.

No records have been removed, corrected, or modified.

## 5. Next actions

- Review the source documentation and variable definitions.
- Investigate whether the values have a consistent explanation.
- Preserve the original source data.
- Document any treatment applied before modeling.

## 6. Inventory Status Validation

### Objective

Validate the consistency between `stock_hour6_22_cnt`
and the hourly vector `hours_stock_status`.

### Results

- Records analyzed: 4,500,000.
- Records with exactly 24 hourly status elements: 4,500,000.
- Hourly status values outside 0 and 1: 0.
- Observed daily stock count range: 0–16.
- Records where the number of ones in positions 6–21 matched
  `stock_hour6_22_cnt`: 4,500,000 (100%).
- Records where the number of zeros in positions 6–21 matched
  `stock_hour6_22_cnt`: 81,818.
- Records where the number of zeros differed from
  `stock_hour6_22_cnt`: 4,388,182.

### Interpretation

The daily stockout count is fully consistent with the number
of ones in positions 6–21 of the hourly status vector.

This supports interpreting value 1 as an out-of-stock status
for the validated 16-hour interval, assuming the hourly vector
starts at 00:00.

The matching results establish numerical consistency under
this hourly alignment assumption. The interpretation should
remain documented as an assumption until confirmed against
the source implementation or definitive variable documentation.

### Data Treatment

No source records were changed, removed, or corrected.

### Modeling Implication

The hourly stock-status vector may help identify periods when
observed sales are constrained by stock availability.

Observed sales should not automatically be interpreted as
unconstrained customer demand during potential stockout periods.

## 7. Time-Series Continuity Validation

### Results

- Records processed: 4,500,000.
- Unique city-store-product series: 50,000.
- Observations per series: exactly 90.
- Series with fewer than 90 observations: 0.
- Series with more than 90 observations: 0.
- Potential missing dates within observed series spans: 0.

### Interpretation

All 50,000 city-store-product series contain 90 observations,
with no missing dates detected between their first and last
observed dates.

This supports the temporal completeness of the supplied
training data for the observed series.

### Data Treatment

No source records were changed, removed, or corrected.

## Discount values greater than 1

### Finding

SQL validation identified 34 records with `discount > 1` out of 4,500,000 total records (approximately 0.00076%).

- Minimum affected value: 1.019
- Maximum affected value: 1.088
- Affected product: product_id 37
- Affected cities: city_id 11 and 15
- Affected stores: 6
- Observed sales range among affected records: 0.4 to 2.5
- Observed `stock_hour6_22_cnt` range among affected records: 0 to 13

### Interpretation

The affected records are concentrated in one product and occur across multiple stores and two cities. This pattern warrants investigation of the source variable and its business definition.

The available evidence does not establish the cause of the values above 1, nor does it establish a causal relationship between discount, observed sales, and stockout exposure.

### Treatment decision

No records were deleted or modified. Values above 1 will be retained in the staging table until the variable definition and source behavior are investigated further.

### Next steps

- Verify the source documentation for the `discount` variable.
- Compare the affected product's records with its other discount values.
- Evaluate whether the anomaly requires a separate analytical flag.
- Document any transformation before using this variable in predictive models.

## 8. Exploratory SQL Analysis Findings

### 8.1 Observed Sales by Date

Daily aggregation of the staging table identified variation in observed sales throughout the 90-day period.

- Records per date: 50,000.
- Minimum daily sum of `sale_amount`: 34,893.48.
- Maximum daily sum of `sale_amount`: 72,938.82.

These sums represent normalized observed sales values. They should not be interpreted as monetary revenue or original physical sales quantities.

### 8.2 Weekday Patterns

Daily averages differed by weekday.

- Sunday: 60,034.71.
- Saturday: 58,906.50.
- Thursday: 43,301.80.

Sunday had the highest observed daily aggregate among the weekdays analyzed, while Thursday had the lowest.

These differences are descriptive and do not establish the cause of the observed patterns.

### 8.3 Holiday Flag Investigation

The dataset contains 90 distinct dates, of which 31 had `holiday_flag = 1`.

The distribution by weekday was:

- Saturday: 13 of 13 dates marked as holidays.
- Sunday: 12 of 13 dates marked as holidays.
- Monday: 1 of 13 dates marked as a holiday.
- Tuesday: 0 of 13 dates marked as holidays.
- Wednesday: 1 of 12 dates marked as a holiday.
- Thursday: 2 of 13 dates marked as holidays.
- Friday: 2 of 13 dates marked as holidays.

The mean `sale_amount` across all records was 0.9140 for non-holiday records and 1.1596 for holiday records, approximately 26.9% higher in the holiday group.

However, the holiday indicator is strongly associated with the day of the week. The comparison may therefore reflect differences in weekday composition rather than an independent holiday effect.

The exact assignment rule for `holiday_flag` remains unconfirmed.

### 8.4 Product 267: Abrupt Observed Sales Change

A comparison of product 267 across 131 stores identified a substantial change between April 26 and April 27, 2024.

- April 26 mean `sale_amount`: 3.7962.
- April 27 mean `sale_amount`: 16.0351.
- Relative increase: approximately 322.4%.
- April 26 mean `stock_hour6_22_cnt`: 12.3817.
- April 27 mean `stock_hour6_22_cnt`: 6.9084.

The change coincided with `holiday_flag` changing from 0 to 1. The mean discount also increased from 0.0458 to 0.0763.

On April 27, 131 records were marked as holidays, and 10 records had a positive discount. No records had `activity_flag = 1`.

The overall dataset mean `sale_amount` also increased between April 26 and April 27, from 0.8612 to 1.2044. The observed change was therefore not exclusive to product 267.

These simultaneous changes do not establish causality. Additional investigation is needed before attributing the increase to holidays, discounts, stock availability, or other factors.

### 8.5 Product-Level Change Classification

A comparison of product-level mean `sale_amount` between April 26 and April 27 classified 865 products into the following mutually exclusive categories:

- Change remaining: 708 products.
- Increase greater than 100%: 68 products.
- Decrease greater than 50%: 35 products.
- Increase greater than 200%: 21 products.
- Baseline mean equal to zero: 20 products.
- Increase greater than 500%: 13 products.

The categories were assigned using sequential CASE conditions, so the higher increase categories are separate rather than cumulative.

Large percentage changes may result from very small baseline values. These percentages should be interpreted alongside absolute changes.

### 8.6 Modeling Implications

The exploratory findings suggest the following considerations for future forecasting work:

- Preserve normalized `sale_amount` as supplied and document its scale.
- Investigate the exact definition of `holiday_flag` before relying on it as an independent holiday feature.
- Consider weekday effects explicitly during feature engineering and model evaluation.
- Account for potential stockout-related limitations when interpreting observed sales as demand.
- Investigate abrupt changes before classifying them as errors or genuine demand shifts.
- Use chronological training and test periods when evaluating forecasting models.
- Compare model performance using appropriate error metrics and document assumptions and limitations.

### 8.7 Data Treatment

No source records were deleted, corrected, or modified as a result of these exploratory analyses.

The findings are descriptive. They do not establish causal relationships between observed sales, holiday flags, discounts, and stock availability.

## 9. Forecast Model Evaluation

### 9.1 Evaluation Setup

Two forecasting approaches were evaluated using the same chronological training and test periods.

- Training/reference period: June 5–11, 2024.
- Test period: June 12–25, 2024.
- Training series: 50,000.
- Test series: 50,000.
- Evaluated records: 700,000 per model.
- Forecasting granularity: individual city-store-product time series.

### 9.2 Models Evaluated

**Model 1: Seven-Day Mean Baseline**

The forecast for each series was calculated as the mean observed sales over the seven-day reference period and held constant throughout the test period.

**Model 2: Weekly Seasonal Naive**

The forecast repeated the observed sales from the corresponding weekday in the reference week.

### 9.3 Performance Results

| Metric | Seven-Day Mean Baseline | Weekly Seasonal Naive |
| ------ | ----------------------: | --------------------: |
| MAE    |                0.428854 |              0.504444 |
| RMSE   |                0.720024 |              0.848539 |
| WAPE   |                  38.05% |                44.76% |

The seven-day mean baseline achieved lower error values across all three metrics for this test period. The weekly seasonal naive model's WAPE was approximately 6.71 percentage points higher.

### 9.4 Interpretation and Limitations

The seven-day mean baseline outperformed the weekly seasonal naive approach under the evaluated configuration and test period. This result does not establish that weekly patterns are generally uninformative; alternative feature engineering, model configurations, and evaluation periods may produce different results.

The target variable, `sale_amount`, represents normalized observed sales rather than confirmed unconstrained demand. Stock availability may limit observed sales, so forecast errors should be interpreted in light of potential stockout effects.

These results establish a baseline for subsequent model development. Further experiments should use chronological evaluation and compare improvements against the baseline on equivalent test records.

### 9.5 Output Files

- `reports/09_baseline_forecast_metrics.csv`
- `reports/10_weekly_seasonal_forecast_metrics.csv`
- `reports/11_forecast_model_comparison.csv`
