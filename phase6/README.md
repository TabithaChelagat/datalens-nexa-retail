# DataLens — Nexa Retail Phase 6 Demo v7

## Workflow

DataLens presents a reproducible data lifecycle:

**Explore → Data Quality → Clean → Transform → Analyze → Ask**

### 1. Explore
The viewer selects one raw CSV and can inspect:
- row and column counts
- column names and data types
- first 5 rows
- missing values
- duplicate rows
- unique values
- numeric statistics
- obvious quality warnings

### 2. Data Quality
The application reports detected issues as:
**Issue | Column | Count | Action**

The findings are computed from the selected raw dataset.

### 3. Clean
Controlled operations include:
- numeric missing values: mean, median, 0, leave unchanged
- categorical missing values: mode, custom value, leave unchanged
- remove duplicate rows
- remove selected columns
- rename columns
- change data type
- standardize text
- handle invalid ages
- handle negative numeric values

Cleaning returns a **Before → Action → After** evidence view.

### 4. Transform
Controlled transformations create a new column from available columns:
- year, month, quarter, day of week from dates
- age group, revenue band, tenure group
- arithmetic calculations between numeric columns

### 5. Analyze
The governed demo layer computes:
- revenue
- profit
- completed orders
- customers
- AOV
- profit margin
- monthly revenue/profit
- store performance
- category performance
- top products

Charts accompany the major analytical tables.

### 6. Ask DataLens
Questions are answered from controlled analytical functions. The fallback demo mode does not send raw CSV contents to the model. Supported examples include category/product rankings, store performance, customer count, monthly trend, KPIs, margin, and data quality.

If an Anthropic API key is configured, the model may use the same governed functions through tool calling. User-facing evidence remains vendor-neutral.

## Files changed in v7

- `phase6/api/index.py` — expanded exploration, quality, cleaning, transformation, analytics and governed Ask logic.
- `phase6/public/index.html` — rebuilt workflow UI, Before/After evidence views, cleaning controls, transformations, charts and clickable questions.
- `phase6/README.md` — updated v7 workflow and implementation notes.

`phase6/vercel.json` and `phase6/requirements.txt` are unchanged from the known-good v6 deployment.


## Phase 6 Demo v8 UI updates
- Explore remains separate from Data Quality.
- Cleaning retains issue/action/effect summaries without before/after row previews.
- Transform exposes date-derived columns only in the UI.
- Analyze uses charts without duplicate tables; store chart groups stores by region with region-specific colors.
- Ask DataLens uses a governed dropdown of business questions with computed answers and matching visualizations.
