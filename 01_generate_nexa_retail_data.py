"""
Nexa Retail — Reproducible synthetic retail data generator
Project: DataLens — AI-Powered Data Quality, Analytics & Management Assistant

Generates:
  data/raw/*.csv          intentionally messy operational data
  data/reference/*.csv   clean ground-truth data
  data/quality/*.json    injected-defect benchmark metadata

Period: 2024-01-01 through 2025-12-31
Scale:
  20,000 customers
  100 products
  20 stores
  150,000 orders
  ~300,000–500,000 order items
  480 monthly target records

Dependencies:
  pandas, numpy
"""

from pathlib import Path
import json
import random
import numpy as np
import pandas as pd

SEED = 20260911
random.seed(SEED)
np.random.seed(SEED)

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
REFERENCE = ROOT / "data" / "reference"
QUALITY = ROOT / "data" / "quality"

for directory in (RAW, REFERENCE, QUALITY):
    directory.mkdir(parents=True, exist_ok=True)

START = pd.Timestamp("2024-01-01")
END = pd.Timestamp("2025-12-31")
N_CUSTOMERS = 20_000
N_PRODUCTS = 100
N_STORES = 20
N_ORDERS = 150_000

FIRST_NAMES = [
    "Amina","Brian","Carol","Daniel","Esther","Faith","Grace","Hassan",
    "Irene","James","Joy","Kevin","Lilian","Martin","Mercy","Naomi",
    "Peter","Ruth","Samuel","Sarah","Victor","Wanjiku","Wilson","Zawadi"
]
LAST_NAMES = [
    "Otieno","Mwangi","Kamau","Kiptoo","Ochieng","Wambui","Njoroge",
    "Kariuki","Cheruiyot","Mutua","Maina","Koech","Kimani","Odhiambo",
    "Chebet","Kiplagat","Muthoni","Akinyi","Wekesa","Nyongesa"
]

CITIES = {
    "Nairobi": 0.34, "Mombasa": 0.14, "Kisumu": 0.10, "Nakuru": 0.10,
    "Eldoret": 0.08, "Thika": 0.06, "Machakos": 0.04, "Kitale": 0.04,
    "Nyeri": 0.03, "Kakamega": 0.03, "Malindi": 0.02, "Naivasha": 0.02
}

REGIONS = {
    "Nairobi": ["Nairobi"],
    "Coast": ["Mombasa", "Malindi"],
    "Western": ["Kisumu", "Kakamega", "Kitale"],
    "Rift Valley": ["Nakuru", "Eldoret", "Naivasha"],
    "Central": ["Thika", "Nyeri"],
    "Eastern": ["Machakos"],
}

CATEGORIES = {
    "Electronics": ["Mobile Phones", "Computers", "Audio", "Accessories"],
    "Home": ["Kitchen", "Furniture", "Appliances", "Home Decor"],
    "Fashion": ["Menswear", "Womenswear", "Footwear", "Accessories"],
    "Beauty": ["Skincare", "Haircare", "Fragrance", "Personal Care"],
    "Grocery": ["Beverages", "Snacks", "Pantry", "Household"],
}

PAYMENT_METHODS = ["M-Pesa", "Card", "Cash", "Bank Transfer"]
ORDER_STATUSES = ["Completed", "Cancelled", "Returned"]

# ----------------------------
# Helpers
# ----------------------------

def weighted_choice(mapping):
    keys = list(mapping.keys())
    probs = np.array(list(mapping.values()), dtype=float)
    probs /= probs.sum()
    return np.random.choice(keys, p=probs)

def random_dates(n, start=START, end=END):
    days = (end - start).days + 1
    return start + pd.to_timedelta(np.random.randint(0, days, n), unit="D")

def money(x):
    return np.round(x, 2)

def add_issue(log, table, issue, count, details=None):
    log.append({
        "table": table,
        "issue": issue,
        "affected_records": int(count),
        "details": details or {}
    })

# ----------------------------
# Clean reference: stores
# ----------------------------

store_rows = []
store_profiles = [
    ("Nairobi", "Nairobi", 1.35),
    ("Nairobi", "Nairobi", 1.25),
    ("Nairobi", "Nairobi", 1.15),
    ("Nairobi", "Nairobi", 1.05),
    ("Central", "Thika", 0.95),
    ("Central", "Nyeri", 0.90),
    ("Eastern", "Machakos", 0.82),
    ("Coast", "Mombasa", 1.10),
    ("Coast", "Mombasa", 0.98),
    ("Coast", "Malindi", 0.72),
    ("Western", "Kisumu", 1.02),
    ("Western", "Kisumu", 0.92),
    ("Western", "Kakamega", 0.78),
    ("Western", "Kitale", 0.80),
    ("Rift Valley", "Nakuru", 1.08),
    ("Rift Valley", "Nakuru", 0.94),
    ("Rift Valley", "Eldoret", 1.00),
    ("Rift Valley", "Eldoret", 0.88),
    ("Rift Valley", "Naivasha", 0.76),
    ("Central", "Nyeri", 0.73),
]
for i, (region, city, performance) in enumerate(store_profiles, 1):
    store_rows.append({
        "store_id": f"ST{i:03d}",
        "store_name": f"Nexa {city} {i}",
        "region": region,
        "city": city,
        "manager": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        "performance_factor": performance,
    })
stores = pd.DataFrame(store_rows)

# ----------------------------
# Clean reference: products
# ----------------------------

product_rows = []
product_templates = {
    "Electronics": [
        ("Mobile Phone", 9000, 65000), ("Laptop", 35000, 140000),
        ("Wireless Earbuds", 2500, 12000), ("Bluetooth Speaker", 3000, 18000),
        ("Power Bank", 1200, 7000), ("Keyboard", 1800, 8000)
    ],
    "Home": [
        ("Blender", 2500, 12000), ("Microwave", 7000, 30000),
        ("Cookware Set", 3500, 18000), ("Office Chair", 6500, 30000),
        ("Table Lamp", 900, 6000), ("Bedsheet Set", 1800, 9000)
    ],
    "Fashion": [
        ("Shirt", 900, 5000), ("Dress", 1800, 9000), ("Jeans", 1800, 8500),
        ("Sneakers", 2500, 15000), ("Handbag", 1800, 10000), ("Belt", 700, 4000)
    ],
    "Beauty": [
        ("Face Moisturizer", 500, 3500), ("Shampoo", 350, 2500),
        ("Perfume", 1500, 12000), ("Hair Oil", 300, 2200),
        ("Body Lotion", 400, 3000), ("Sunscreen", 500, 3500)
    ],
    "Grocery": [
        ("Coffee", 300, 1800), ("Tea", 200, 1400), ("Cooking Oil", 250, 2200),
        ("Cereal", 250, 1800), ("Biscuits", 100, 700), ("Cleaning Liquid", 180, 1500)
    ],
}
for i in range(N_PRODUCTS):
    category = list(CATEGORIES.keys())[i // (N_PRODUCTS // len(CATEGORIES))]
    if category not in CATEGORIES:
        category = "Grocery"
    subcategory = random.choice(CATEGORIES[category])
    template, low, high = random.choice(product_templates[category])
    name = f"{template} {chr(65 + (i % 26))}{(i // 26) + 1}"
    selling = np.random.uniform(low, high)
    margin = np.random.uniform(0.12, 0.38)
    cost = selling * (1 - margin)
    product_rows.append({
        "product_id": f"PR{i+1:03d}",
        "product_name": name,
        "category": category,
        "subcategory": subcategory,
        "unit_cost": money(cost),
        "selling_price": money(selling),
    })
products = pd.DataFrame(product_rows)

# ----------------------------
# Clean reference: customers
# ----------------------------

customer_cities = np.random.choice(
    list(CITIES.keys()), size=N_CUSTOMERS, p=np.array(list(CITIES.values()))
)
customer_rows = []
reg_dates = random_dates(N_CUSTOMERS, pd.Timestamp("2023-01-01"), END)
for i in range(N_CUSTOMERS):
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    customer_rows.append({
        "customer_id": f"CUST{i+1:05d}",
        "customer_name": f"{first} {last}",
        "email": f"{first.lower()}.{last.lower()}{i+1}@example.com",
        "phone": f"07{np.random.randint(10000000, 99999999)}",
        "gender": np.random.choice(["Female", "Male"], p=[0.53, 0.47]),
        "date_of_birth": (
            pd.Timestamp("1960-01-01") +
            pd.to_timedelta(np.random.randint(0, 55 * 365, N_CUSTOMERS)[i], unit="D")
        ),
        "city": customer_cities[i],
        "registration_date": reg_dates[i],
    })
customers = pd.DataFrame(customer_rows)

# ----------------------------
# Clean reference: orders
# ----------------------------

# Customer propensity: a small number of customers buy much more often.
customer_weights = np.random.lognormal(mean=0, sigma=1.0, size=N_CUSTOMERS)
customer_weights /= customer_weights.sum()

# Store performance affects order volume.
store_weights = stores["performance_factor"].to_numpy()
store_weights /= store_weights.sum()

dates = pd.date_range(START, END, freq="D")
# Mild seasonality + month-end uplift.
month_factor = {
    1: 0.90, 2: 0.92, 3: 0.98, 4: 1.00, 5: 1.04, 6: 1.00,
    7: 1.02, 8: 1.05, 9: 1.00, 10: 1.08, 11: 1.18, 12: 1.30
}
date_weights = np.array([
    month_factor[d.month] * (1.10 if d.day >= 25 else 1.0)
    for d in dates
], dtype=float)
date_weights /= date_weights.sum()

order_dates = np.random.choice(dates, size=N_ORDERS, p=date_weights)
order_customer_idx = np.random.choice(np.arange(N_CUSTOMERS), size=N_ORDERS, p=customer_weights)
order_store_idx = np.random.choice(np.arange(N_STORES), size=N_ORDERS, p=store_weights)

order_rows = []
for i in range(N_ORDERS):
    status = np.random.choice(ORDER_STATUSES, p=[0.91, 0.055, 0.035])
    order_rows.append({
        "order_id": f"ORD{i+1:06d}",
        "customer_id": customers.iloc[order_customer_idx[i]]["customer_id"],
        "store_id": stores.iloc[order_store_idx[i]]["store_id"],
        "order_date": pd.Timestamp(order_dates[i]),
        "order_status": status,
        "payment_method": np.random.choice(PAYMENT_METHODS, p=[0.48, 0.30, 0.12, 0.10]),
    })
orders = pd.DataFrame(order_rows)

# ----------------------------
# Clean reference: order items
# ----------------------------

# More items per order, with 1–5 line items.
n_items_per_order = np.random.choice([1,2,3,4,5], size=N_ORDERS, p=[0.48,0.28,0.14,0.07,0.03])
total_items = int(n_items_per_order.sum())

item_order_ids = np.repeat(orders["order_id"].to_numpy(), n_items_per_order)
product_idx = np.random.choice(np.arange(N_PRODUCTS), size=total_items)
qty = np.random.choice([1,2,3,4,5], size=total_items, p=[0.54,0.24,0.12,0.07,0.03])

item_rows = []
for i in range(total_items):
    p = products.iloc[product_idx[i]]
    # Actual price fluctuates modestly around master selling price.
    actual_price = p["selling_price"] * np.random.uniform(0.97, 1.03)
    discount = np.random.choice(
        [0, 0.05, 0.10, 0.15, 0.20],
        p=[0.35,0.25,0.22,0.14,0.04]
    )
    item_rows.append({
        "order_item_id": f"ITEM{i+1:07d}",
        "order_id": item_order_ids[i],
        "product_id": p["product_id"],
        "quantity": int(qty[i]),
        "unit_price": money(actual_price),
        "discount": discount,
    })
order_items = pd.DataFrame(item_rows)

# ----------------------------
# Clean reference: monthly targets
# ----------------------------

months = pd.date_range(START, END, freq="MS")
target_rows = []
for month in months:
    for _, store in stores.iterrows():
        # Target reflects store capacity and mild annual growth.
        year_growth = 1.00 if month.year == 2024 else 1.08
        base = 1_100_000 * store["performance_factor"] / 20
        seasonal = month_factor[month.month]
        revenue_target = base * seasonal * year_growth
        profit_target = revenue_target * np.random.uniform(0.18, 0.24)
        target_rows.append({
            "target_id": f"TGT{len(target_rows)+1:05d}",
            "store_id": store["store_id"],
            "month": month,
            "revenue_target": money(revenue_target),
            "profit_target": money(profit_target),
        })
sales_targets = pd.DataFrame(target_rows)

# Save clean reference.
reference_tables = {
    "customers": customers,
    "products": products,
    "stores": stores.drop(columns=["performance_factor"]),
    "orders": orders,
    "order_items": order_items,
    "sales_targets": sales_targets,
}
for name, df in reference_tables.items():
    df.to_csv(REFERENCE / f"{name}_clean.csv", index=False)

# ----------------------------
# Create intentionally messy RAW copies
# ----------------------------

quality_log = []

raw_customers = customers.copy()
raw_products = products.copy()
raw_stores = stores.drop(columns=["performance_factor"]).copy()
raw_orders = orders.copy()
raw_items = order_items.copy()
raw_targets = sales_targets.copy()

# Customers: missing email/phone.
idx = np.random.choice(raw_customers.index, size=round(len(raw_customers)*0.03), replace=False)
raw_customers.loc[idx, "email"] = None
add_issue(quality_log, "customers", "missing_email", len(idx))

idx = np.random.choice(raw_customers.index, size=round(len(raw_customers)*0.02), replace=False)
raw_customers.loc[idx, "phone"] = None
add_issue(quality_log, "customers", "missing_phone", len(idx))

# Customers: inconsistent cities.
city_map = {"Nairobi":"Nairobi ", "Mombasa":"Mombasa City", "Kisumu":"KISUMU", "Nakuru":"Nakuru "}
idx = np.random.choice(raw_customers.index, size=round(len(raw_customers)*0.015), replace=False)
for j in idx:
    raw_customers.loc[j, "city"] = city_map.get(raw_customers.loc[j, "city"], raw_customers.loc[j, "city"])
add_issue(quality_log, "customers", "inconsistent_city_labels", len(idx), city_map)

# Customers: future DOBs.
idx = np.random.choice(raw_customers.index, size=round(len(raw_customers)*0.002), replace=False)
raw_customers.loc[idx, "date_of_birth"] = pd.Timestamp("2035-01-01")
add_issue(quality_log, "customers", "future_date_of_birth", len(idx))

# Customers: duplicate records.
dup_idx = np.random.choice(raw_customers.index, size=round(len(raw_customers)*0.01), replace=False)
dups = raw_customers.loc[dup_idx].copy()
dups["customer_id"] = dups["customer_id"] + "_DUP"
raw_customers = pd.concat([raw_customers, dups], ignore_index=True)
add_issue(quality_log, "customers", "duplicate_customer_records", len(dups))

# Products: category inconsistencies.
idx = np.random.choice(raw_products.index, size=round(len(raw_products)*0.05), replace=False)
raw_products.loc[idx, "category"] = raw_products.loc[idx, "category"].replace({
    "Electronics":"electronics", "Home":"HOME", "Fashion":"fashion",
    "Beauty":"BEAUTY", "Grocery":"grocery"
})
add_issue(quality_log, "products", "inconsistent_category_labels", len(idx))

# Products: missing subcategory.
idx = np.random.choice(raw_products.index, size=5, replace=False)
raw_products.loc[idx, "subcategory"] = None
add_issue(quality_log, "products", "missing_subcategory", len(idx))

# Products: cost > selling price.
idx = np.random.choice(raw_products.index, size=4, replace=False)
raw_products.loc[idx, "unit_cost"] = raw_products.loc[idx, "selling_price"] * 1.12
raw_products.loc[idx, "unit_cost"] = raw_products.loc[idx, "unit_cost"].round(2)
add_issue(quality_log, "products", "unit_cost_exceeds_selling_price", len(idx))

# Stores: inconsistent region labels.
idx = np.random.choice(raw_stores.index, size=4, replace=False)
raw_stores.loc[idx, "region"] = raw_stores.loc[idx, "region"].replace({
    "Nairobi":"nairobi", "Coast":"COAST", "Western":"western",
    "Rift Valley":"Rift valley", "Central":"central", "Eastern":"EASTERN"
})
add_issue(quality_log, "stores", "inconsistent_region_labels", len(idx))

# Stores: duplicate records.
dup_idx = np.random.choice(raw_stores.index, size=2, replace=False)
store_dups = raw_stores.loc[dup_idx].copy()
store_dups["store_id"] = store_dups["store_id"] + "_DUP"
raw_stores = pd.concat([raw_stores, store_dups], ignore_index=True)
add_issue(quality_log, "stores", "duplicate_store_records", len(store_dups))

# Orders: duplicate IDs.
idx = np.random.choice(raw_orders.index, size=round(len(raw_orders)*0.005), replace=False)
raw_orders.loc[idx, "order_id"] = raw_orders.loc[idx, "order_id"].astype(str)
# Make duplicate IDs by copying IDs from other valid orders.
source_idx = np.random.choice(raw_orders.index, size=len(idx), replace=False)
raw_orders.loc[idx, "order_id"] = raw_orders.loc[source_idx, "order_id"].to_numpy()
add_issue(quality_log, "orders", "duplicate_order_ids", len(idx))

# Orders: invalid foreign keys.
idx = np.random.choice(raw_orders.index, size=round(len(raw_orders)*0.005), replace=False)
raw_orders.loc[idx, "customer_id"] = "CUST99999X"
add_issue(quality_log, "orders", "invalid_customer_foreign_keys", len(idx))

idx = np.random.choice(raw_orders.index, size=round(len(raw_orders)*0.003), replace=False)
raw_orders.loc[idx, "store_id"] = "ST999"
add_issue(quality_log, "orders", "invalid_store_foreign_keys", len(idx))

# Orders: inconsistent payment labels.
idx = np.random.choice(raw_orders.index, size=round(len(raw_orders)*0.01), replace=False)
raw_orders.loc[idx, "payment_method"] = raw_orders.loc[idx, "payment_method"].replace({
    "M-Pesa":"M-PESA", "Card":"card", "Cash":"CASH", "Bank Transfer":"bank transfer"
})
add_issue(quality_log, "orders", "inconsistent_payment_labels", len(idx))

# Orders: future dates.
idx = np.random.choice(raw_orders.index, size=round(len(raw_orders)*0.001), replace=False)
raw_orders.loc[idx, "order_date"] = pd.Timestamp("2027-01-15")
add_issue(quality_log, "orders", "future_order_dates", len(idx))

# Order items: zero/negative quantities.
idx = np.random.choice(raw_items.index, size=round(len(raw_items)*0.004), replace=False)
half = len(idx)//2
raw_items.loc[idx[:half], "quantity"] = 0
raw_items.loc[idx[half:], "quantity"] = -np.random.randint(1, 4, len(idx)-half)
add_issue(quality_log, "order_items", "non_positive_quantity", len(idx))

# Order items: invalid product foreign keys.
idx = np.random.choice(raw_items.index, size=round(len(raw_items)*0.003), replace=False)
raw_items.loc[idx, "product_id"] = "PR999"
add_issue(quality_log, "order_items", "invalid_product_foreign_keys", len(idx))

# Order items: abnormal discounts.
idx = np.random.choice(raw_items.index, size=round(len(raw_items)*0.01), replace=False)
raw_items.loc[idx, "discount"] = np.random.choice([0.55, 0.75, 1.20], len(idx))
add_issue(quality_log, "order_items", "abnormal_discount", len(idx))

# Order items: price mismatches.
idx = np.random.choice(raw_items.index, size=round(len(raw_items)*0.01), replace=False)
raw_items.loc[idx, "unit_price"] = money(raw_items.loc[idx, "unit_price"] * np.random.uniform(1.4, 2.0, len(idx)))
add_issue(quality_log, "order_items", "price_mismatch_against_master", len(idx))

# Targets: duplicate store-month combinations.
dup_idx = np.random.choice(raw_targets.index, size=10, replace=False)
target_dups = raw_targets.loc[dup_idx].copy()
target_dups["target_id"] = [f"TGT_DUP{i+1:03d}" for i in range(len(target_dups))]
raw_targets = pd.concat([raw_targets, target_dups], ignore_index=True)
add_issue(quality_log, "sales_targets", "duplicate_store_month_targets", len(target_dups))

# Targets: missing values.
idx = np.random.choice(raw_targets.index, size=8, replace=False)
raw_targets.loc[idx, "revenue_target"] = None
add_issue(quality_log, "sales_targets", "missing_revenue_target", len(idx))

# Save raw tables.
raw_tables = {
    "customers_raw": raw_customers,
    "products_raw": raw_products,
    "stores_raw": raw_stores,
    "orders_raw": raw_orders,
    "order_items_raw": raw_items,
    "sales_targets_raw": raw_targets,
}
for name, df in raw_tables.items():
    df.to_csv(RAW / f"{name}.csv", index=False)

# Quality benchmark.
benchmark = {
    "project": "DataLens — Nexa Retail",
    "seed": SEED,
    "period": {"start": str(START.date()), "end": str(END.date())},
    "expected_scale": {
        "customers": N_CUSTOMERS,
        "products": N_PRODUCTS,
        "stores": N_STORES,
        "orders": N_ORDERS,
        "order_items": int(total_items),
        "sales_targets": int(len(sales_targets)),
    },
    "injected_issues": quality_log,
}
with open(QUALITY / "injected_quality_benchmark.json", "w", encoding="utf-8") as f:
    json.dump(benchmark, f, indent=2, default=str)

# Summary.
print("=" * 72)
print("NEXA RETAIL — SYNTHETIC DATA GENERATION COMPLETE")
print("=" * 72)
for name, df in raw_tables.items():
    print(f"{name:22s}: {len(df):,} rows")
print("-" * 72)
print(f"Reference files : {REFERENCE}")
print(f"Raw files       : {RAW}")
print(f"Quality benchmark: {QUALITY / 'injected_quality_benchmark.json'}")
print("=" * 72)
