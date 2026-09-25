import json, os, urllib.request
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import pandas as pd

API_ROOT = Path(__file__).resolve().parent
RAW = API_ROOT / "data" / "raw"
SUPPORTED = {".csv"}
MAX_ROWS = 100


def json_default(v):
    if pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return str(v)


def send(h, status, payload):
    body = json.dumps(payload, default=json_default).encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Access-Control-Allow-Origin", "*")
    h.send_header("Access-Control-Allow-Headers", "Content-Type")
    h.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    h.end_headers()
    h.wfile.write(body)


def files():
    return sorted(p.name for p in RAW.glob("*.csv") if p.suffix.lower() in SUPPORTED)


def load(name):
    if name not in files():
        raise ValueError("Unknown demo dataset.")
    return pd.read_csv(RAW / name)


def clean_preview(df, n=5):
    return df.head(n).where(pd.notna(df.head(n)), None).to_dict("records")


def profile(df):
    miss = df.isna().sum()
    cols = []
    for c in df.columns:
        s = df[c]
        cols.append({
            "column": str(c),
            "dtype": str(s.dtype),
            "missing": int(s.isna().sum()),
            "unique": int(s.nunique(dropna=True)),
            "sample_values": [str(x) for x in s.dropna().head(4).tolist()],
        })
    numeric = df.select_dtypes(include="number")
    stats = []
    for c in numeric.columns:
        x = numeric[c]
        stats.append({
            "column": str(c),
            "count": int(x.count()),
            "min": x.min(),
            "mean": x.mean(),
            "median": x.median(),
            "max": x.max(),
            "std": x.std(),
        })
    warnings = []
    for c, n in df.isna().items():
        count = int(n.sum())
        if count:
            warnings.append({
                "type": "Missing values",
                "column": str(c),
                "count": count,
                "message": f"{count:,} missing value(s) detected in {c}."
            })
    dup = int(df.duplicated().sum())
    if dup:
        warnings.append({
            "type": "Duplicate rows",
            "column": "—",
            "count": dup,
            "message": f"{dup:,} duplicate row(s) detected."
        })
    for c in df.select_dtypes(include="number").columns:
        neg = int((df[c] < 0).sum())
        if neg:
            warnings.append({
                "type": "Negative values",
                "column": str(c),
                "count": neg,
                "message": f"{neg:,} negative value(s) detected in {c}; review whether they are valid."
            })
    if "age" in df.columns:
        age = pd.to_numeric(df["age"], errors="coerce")
        bad = int(((age < 0) | (age > 120)).sum())
        if bad:
            warnings.append({
                "type": "Out-of-range age",
                "column": "age",
                "count": bad,
                "message": f"{bad:,} age value(s) fall outside the 0–120 range."
            })
    return {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "column_names": [str(c) for c in df.columns],
        "duplicates": int(df.duplicated().sum()),
        "missing_cells": int(miss.sum()),
        "column_profile": cols,
        "numeric_summary": stats,
        "warnings": warnings,
        "preview": clean_preview(df, 5),
    }


def quality(df):
    issues = []
    for c, n in df.isna().sum().items():
        n = int(n)
        if n:
            numeric = pd.api.types.is_numeric_dtype(df[c])
            action = "Mean / median / 0 / leave unchanged" if numeric else "Mode / custom value / leave unchanged"
            issues.append({
                "type": "Missing values",
                "column": str(c),
                "count": n,
                "severity": "High" if n / max(len(df), 1) > .05 else "Medium",
                "suggested_action": action,
            })
    d = int(df.duplicated().sum())
    if d:
        issues.append({
            "type": "Duplicate rows",
            "column": "—",
            "count": d,
            "severity": "Medium",
            "suggested_action": "Remove duplicate rows",
        })
    for c in df.select_dtypes(include="number").columns:
        neg = int((df[c] < 0).sum())
        if neg:
            issues.append({
                "type": "Negative values",
                "column": str(c),
                "count": neg,
                "severity": "High",
                "suggested_action": "Review or handle invalid values",
            })
    if "age" in df.columns:
        age = pd.to_numeric(df["age"], errors="coerce")
        bad = int(((age < 0) | (age > 120)).sum())
        if bad:
            issues.append({
                "type": "Invalid values",
                "column": "age",
                "count": bad,
                "severity": "High",
                "suggested_action": "Replace invalid ages with median or leave unchanged",
            })
    return {"issue_count": len(issues), "issues": issues}


def clean_df(df, ops):
    out = df.copy()
    log = []

    if ops.get("drop_duplicates"):
        before = len(out)
        out = out.drop_duplicates()
        log.append({
            "column": "—",
            "issue": "Duplicate rows",
            "action": "Remove duplicate rows",
            "before": int(before - len(out) + (len(out))),
            "changed": int(before - len(out)),
            "after": int(len(out)),
        })

    for col in ops.get("drop_columns", []):
        if col in out.columns:
            before = len(out.columns)
            out = out.drop(columns=[col])
            log.append({
                "column": col, "issue": "Column removal",
                "action": "Remove selected column", "before": before,
                "changed": 1, "after": len(out.columns)
            })

    rename = ops.get("rename_columns", {})
    valid_rename = {k: v for k, v in rename.items() if k in out.columns and str(v).strip()}
    if valid_rename:
        out = out.rename(columns=valid_rename)
        for old, new in valid_rename.items():
            log.append({
                "column": old, "issue": "Column name", "action": f"Rename to {new}",
                "before": old, "changed": 1, "after": new
            })

    for col, method in ops.get("fill_nulls", {}).items():
        if col not in out.columns:
            continue
        before = int(out[col].isna().sum())
        if not before:
            continue
        s = out[col]
        if method == "mean" and pd.api.types.is_numeric_dtype(s):
            val = s.mean()
        elif method == "median" and pd.api.types.is_numeric_dtype(s):
            val = s.median()
        elif method == "mode":
            m = s.mode()
            val = m.iloc[0] if not m.empty else 0
        elif method == "zero":
            val = 0
        elif method == "custom":
            val = ops.get("custom_values", {}).get(col, "")
        else:
            continue
        out[col] = s.fillna(val)
        log.append({
            "column": col, "issue": "Missing values",
            "action": f"Fill with {method}" + (f" ({val})" if method == "custom" else ""),
            "before": before, "changed": before,
            "after": int(out[col].isna().sum()), "value": val
        })

    for col, dtype in ops.get("change_types", {}).items():
        if col not in out.columns:
            continue
        before = str(out[col].dtype)
        try:
            if dtype == "integer":
                out[col] = pd.to_numeric(out[col], errors="coerce").round().astype("Int64")
            elif dtype == "number":
                out[col] = pd.to_numeric(out[col], errors="coerce")
            elif dtype == "text":
                out[col] = out[col].astype("string")
            elif dtype == "date":
                out[col] = pd.to_datetime(out[col], errors="coerce")
            else:
                continue
            log.append({
                "column": col, "issue": "Data type",
                "action": f"Change type to {dtype}",
                "before": before, "changed": 1, "after": str(out[col].dtype)
            })
        except Exception:
            pass

    for col in ops.get("standardize_text", []):
        if col in out.columns:
            before_unique = int(out[col].nunique(dropna=True))
            out[col] = out[col].map(lambda x: " ".join(str(x).strip().split()).lower() if pd.notna(x) else x)
            log.append({
                "column": col, "issue": "Text standardization",
                "action": "Trim spaces + lowercase",
                "before": before_unique,
                "changed": 1,
                "after": int(out[col].nunique(dropna=True))
            })

    if ops.get("fix_age") and "age" in out.columns:
        age = pd.to_numeric(out["age"], errors="coerce")
        bad = (age < 0) | (age > 120)
        n = int(bad.sum())
        valid = age[~bad]
        med = valid.median()
        if n:
            out.loc[bad, "age"] = med
        log.append({
            "column": "age", "issue": "Invalid values",
            "action": "Replace invalid ages with median",
            "before": n, "changed": n,
            "after": int(((pd.to_numeric(out["age"], errors="coerce") < 0) |
                          (pd.to_numeric(out["age"], errors="coerce") > 120)).sum()),
            "value": med
        })

    if ops.get("fix_negative"):
        for col in out.select_dtypes(include="number").columns:
            vals = pd.to_numeric(out[col], errors="coerce")
            bad = vals < 0
            n = int(bad.sum())
            if n:
                med = vals[~bad].median()
                out.loc[bad, col] = med
                log.append({
                    "column": col, "issue": "Negative values",
                    "action": "Replace negative values with non-negative median",
                    "before": n, "changed": n,
                    "after": int((pd.to_numeric(out[col], errors="coerce") < 0).sum()),
                    "value": med
                })
    return out, log


def apply_transform(df, spec):
    out = df.copy()
    name = str(spec.get("new_column") or "derived_column").strip()
    typ = spec.get("type")
    source = spec.get("source_column")
    if not name:
        raise ValueError("Enter a new column name.")
    if source not in out.columns:
        raise ValueError("Source column not found.")

    if typ in ("year", "month", "quarter", "day_of_week"):
        dt = pd.to_datetime(out[source], errors="coerce")
        if typ == "year":
            out[name] = dt.dt.year
        elif typ == "month":
            out[name] = dt.dt.month_name()
        elif typ == "quarter":
            out[name] = "Q" + dt.dt.quarter.astype("Int64").astype(str)
        else:
            out[name] = dt.dt.day_name()
    elif typ in ("age_group", "revenue_band", "tenure_group"):
        values = pd.to_numeric(out[source], errors="coerce")
        if typ == "age_group":
            bins = [0, 25, 35, 45, 55, float("inf")]
            labels = ["18–25", "26–35", "36–45", "46–55", "56+"]
            out[name] = pd.cut(values, bins=bins, labels=labels, right=True, include_lowest=True)
            out.loc[(values < 18) | (values.isna()), name] = pd.NA
        elif typ == "revenue_band":
            labels = ["Low", "Medium", "High", "Very high"]
            try:
                out[name] = pd.qcut(values, q=4, labels=labels, duplicates="drop")
            except Exception:
                out[name] = pd.cut(values, bins=4, labels=labels)
        else:
            bins = [-float("inf"), 90, 365, 730, float("inf")]
            labels = ["<3 months", "3–12 months", "1–2 years", "2+ years"]
            out[name] = pd.cut(values, bins=bins, labels=labels)
    elif typ == "calculation":
        second = spec.get("second_column")
        op = spec.get("operator", "multiply")
        if second not in out.columns:
            raise ValueError("Second column not found.")
        a = pd.to_numeric(out[source], errors="coerce")
        b = pd.to_numeric(out[second], errors="coerce")
        if op == "multiply":
            out[name] = a * b
        elif op == "add":
            out[name] = a + b
        elif op == "subtract":
            out[name] = a - b
        elif op == "divide":
            out[name] = a / b.replace(0, pd.NA)
        else:
            raise ValueError("Unsupported calculation.")
    else:
        raise ValueError("Unsupported transformation.")
    return out


def analytics():
    c = load("customers.csv")
    o = load("orders.csv")
    i = load("order_items.csv")
    p = load("products.csv")
    s = load("stores.csv")
    c, _ = clean_df(c, {"drop_duplicates": True, "fill_nulls": {"age": "median"}, "fix_age": True})
    o, _ = clean_df(o, {"drop_duplicates": True})
    i, _ = clean_df(i, {"drop_duplicates": True, "fill_nulls": {"quantity": "median"}})
    p, _ = clean_df(p, {"fill_nulls": {"unit_price": "median"}})
    i = i.merge(p[["product_id", "product_name", "category", "unit_price", "unit_cost"]], on="product_id", how="left")
    i["revenue"] = i["quantity"] * i["unit_price"] * (1 - i["discount"].fillna(0))
    i["profit"] = i["revenue"] - i["quantity"] * i["unit_cost"]
    i = i.merge(o[["order_id", "order_date", "store_id", "customer_id", "status"]], on="order_id", how="left")
    completed = i[i.status.eq("Completed")].copy()
    completed["month"] = pd.to_datetime(completed.order_date, errors="coerce").dt.to_period("M").astype(str)
    revenue = float(completed.revenue.sum())
    profit = float(completed.profit.sum())
    orders = int(completed.order_id.nunique())
    customers = int(o[o.status.eq("Completed")].customer_id.nunique())
    monthly = completed[completed["month"].ne("NaT")].groupby("month", dropna=True).agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index().tail(24)
    by_store = completed.groupby("store_id").agg(revenue=("revenue", "sum"), profit=("profit", "sum"), orders=("order_id", "nunique")).reset_index().merge(s, on="store_id", how="left")
    by_store["profit_margin"] = by_store["profit"].div(by_store["revenue"]).fillna(0)
    by_store["aov"] = by_store["revenue"].div(by_store["orders"].replace(0, pd.NA)).fillna(0)
    by_store["revenue_per_order"] = by_store["aov"]
    by_store = by_store.sort_values("revenue", ascending=False).head(10)
    by_cat = completed.groupby("category").agg(revenue=("revenue", "sum"), profit=("profit", "sum"), orders=("order_id", "nunique")).reset_index()
    by_cat["profit_margin"] = by_cat["profit"].div(by_cat["revenue"]).fillna(0)
    by_cat["avg_discount"] = completed.groupby("category")["discount"].mean().reindex(by_cat["category"]).fillna(0).values
    by_cat = by_cat.sort_values("revenue", ascending=False)
    top_products = completed.groupby(["product_id", "product_name"]).agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index()
    top_products["profit_margin"] = top_products["profit"].div(top_products["revenue"]).fillna(0)
    top_products = top_products.sort_values("revenue", ascending=False).head(10)
    by_region = completed.merge(s[["store_id","region"]], on="store_id", how="left").groupby("region").agg(
        revenue=("revenue","sum"), profit=("profit","sum"), orders=("order_id","nunique")
    ).reset_index()
    by_region["profit_margin"] = by_region["profit"].div(by_region["revenue"]).fillna(0)
    by_region = by_region.sort_values("revenue", ascending=False)
    return {
        "kpis": {"revenue": revenue, "profit": profit, "orders": orders, "customers": customers,
                 "aov": revenue / orders if orders else 0, "profit_margin": profit / revenue if revenue else 0,
                 "avg_discount": float(completed["discount"].mean()) if len(completed) else 0},
        "monthly": monthly.to_dict("records"), "stores": by_store.to_dict("records"),
        "categories": by_cat.to_dict("records"), "top_products": top_products.to_dict("records"),
        "regions": by_region.to_dict("records")
    }


def tool_result(tool, args):
    a = analytics()
    if tool == "get_kpi_summary": return a["kpis"]
    if tool == "top_categories": return a["categories"][:int(args.get("n", 3))]
    if tool == "top_products": return a["top_products"][:int(args.get("n", 5))]
    if tool == "store_performance": return a["stores"]
    if tool == "monthly_trend": return a["monthly"]
    if tool == "customer_summary": return {"customers": a["kpis"]["customers"], "orders": a["kpis"]["orders"], "aov": a["kpis"]["aov"]}
    if tool == "data_quality_report": return {f: quality(load(f)) for f in files()}
    raise ValueError("Unknown tool")


def local_answer(question):
    a = analytics()
    q = " ".join(question.lower().strip().split())
    r = a["regions"]
    stores = a["stores"]
    cats = a["categories"]
    products = a["top_products"]
    months = a["monthly"]

    if "region generates the most revenue" in q:
        x=r.iloc[0] if hasattr(r, "iloc") else r[0]
        return f"{x['region']} generates the most revenue at {x['revenue']:.2f}.", "region_revenue"
    if "region generates the most profit" in q:
        x=max(r, key=lambda z:z["profit"])
        return f"{x['region']} generates the most profit at {x['profit']:.2f}.", "region_profit"
    if "highest profit margin" in q and "store" in q:
        x=max(stores, key=lambda z:z["profit_margin"])
        return f"{x['store_name']} has the highest store-level profit margin at {x['profit_margin']:.1%}.", "store_margin"
    if "lowest profit margin" in q and "store" in q:
        x=min(stores, key=lambda z:z["profit_margin"])
        return f"{x['store_name']} has the lowest store-level profit margin at {x['profit_margin']:.1%}.", "store_margin"
    if "category has the highest profit margin" in q:
        x=max(cats, key=lambda z:z["profit_margin"])
        return f"{x['category']} has the highest category profit margin at {x['profit_margin']:.1%}.", "category_margin"
    if "category contributes the most profit" in q:
        x=max(cats, key=lambda z:z["profit"])
        return f"{x['category']} contributes the most profit at {x['profit']:.2f}.", "category_profit"
    if "product generates the most profit" in q:
        x=max(products, key=lambda z:z["profit"])
        return f"{x['product_name']} generates the most profit at {x['profit']:.2f}.", "product_profit"
    if "product has the lowest profit margin" in q:
        x=min(products, key=lambda z:z["profit_margin"])
        return f"Among the top 10 products by revenue, {x['product_name']} has the lowest profit margin at {x['profit_margin']:.1%}.", "product_margin"
    if "month had the highest revenue" in q:
        x=max(months, key=lambda z:z["revenue"])
        return f"{x['month']} had the highest monthly revenue at {x['revenue']:.2f}.", "monthly_revenue"
    if "month had the lowest revenue" in q:
        x=min(months, key=lambda z:z["revenue"])
        return f"{x['month']} had the lowest monthly revenue at {x['revenue']:.2f}.", "monthly_revenue"
    if "month had the highest profit" in q:
        x=max(months, key=lambda z:z["profit"])
        return f"{x['month']} had the highest monthly profit at {x['profit']:.2f}.", "monthly_profit"
    if "highest average order value" in q:
        x=max(stores, key=lambda z:z["aov"])
        return f"{x['store_name']} has the highest average order value at {x['aov']:.2f}.", "store_aov"
    if "region has the most completed orders" in q:
        x=max(r, key=lambda z:z["orders"])
        return f"{x['region']} has the most completed orders, with {x['orders']:,}.", "region_orders"
    if "share of revenue comes from the top category" in q:
        x=cats[0]
        share=x["revenue"]/a["kpis"]["revenue"] if a["kpis"]["revenue"] else 0
        return f"{x['category']} contributes {share:.1%} of completed revenue.", "category_share"
    if "share of revenue comes from the top 3 products" in q:
        share=sum(x["revenue"] for x in products[:3])/a["kpis"]["revenue"] if a["kpis"]["revenue"] else 0
        return f"The top 3 products shown contribute {share:.1%} of completed revenue.", "product_share"
    if "how many customers" in q:
        return f"There are {a['kpis']['customers']:,} customers associated with completed orders in the governed analytics dataset.", "customers"
    if "average discount" in q and "category" not in q:
        return f"The average discount on completed sales is {a['kpis']['avg_discount']:.1%}.", "discount"
    if "category has the highest average discount" in q:
        x=max(cats, key=lambda z:z["avg_discount"])
        return f"{x['category']} has the highest average discount at {x['avg_discount']:.1%}.", "category_discount"
    if "highest revenue per order" in q:
        x=max(stores, key=lambda z:z["revenue_per_order"])
        return f"{x['store_name']} has the highest revenue per completed order at {x['revenue_per_order']:.2f}.", "store_aov"
    if "data-quality issues" in q or "data quality" in q:
        total = sum(quality(load(f))["issue_count"] for f in files())
        return f"The raw demo files contain {total} detected issue type(s). The Data Quality stage provides the file-level findings and counts.", "quality"
    return "Select one of the governed DataLens questions to receive a computed answer and visualization.", None


def chart_for(kind):
    a = analytics()
    if kind == "region_revenue":
        return {"type":"bar","title":"Revenue by region","labels":[x["region"] for x in a["regions"]],"datasets":[{"label":"Revenue","data":[x["revenue"] for x in a["regions"]],"backgroundColor":["#2563eb","#16a34a","#f59e0b","#9333ea"]}]}
    if kind == "region_profit":
        rows=sorted(a["regions"],key=lambda x:x["profit"],reverse=True)
        return {"type":"bar","title":"Profit by region","labels":[x["region"] for x in rows],"datasets":[{"label":"Profit","data":[x["profit"] for x in rows],"backgroundColor":["#2563eb","#16a34a","#f59e0b","#9333ea"]}]}
    if kind == "store_margin":
        rows=sorted(a["stores"],key=lambda x:x["profit_margin"],reverse=True)
        return {"type":"bar","title":"Store profit margin","labels":[x["store_name"] for x in rows],"datasets":[{"label":"Margin","data":[x["profit_margin"]*100 for x in rows],"backgroundColor":"#5aa9e6"}]}
    if kind == "category_margin":
        rows=sorted(a["categories"],key=lambda x:x["profit_margin"],reverse=True)
        return {"type":"bar","title":"Category profit margin","labels":[x["category"] for x in rows],"datasets":[{"label":"Margin %","data":[x["profit_margin"]*100 for x in rows],"backgroundColor":"#5aa9e6"}]}
    if kind == "category_profit":
        rows=sorted(a["categories"],key=lambda x:x["profit"],reverse=True)
        return {"type":"bar","title":"Profit by category","labels":[x["category"] for x in rows],"datasets":[{"label":"Profit","data":[x["profit"] for x in rows],"backgroundColor":"#5aa9e6"}]}
    if kind in ("product_profit","product_margin"):
        rows=sorted(a["top_products"],key=lambda x:x["profit" if kind=="product_profit" else "profit_margin"],reverse=(kind=="product_profit"))
        return {"type":"bar","title":"Product profitability","labels":[x["product_name"] for x in rows],"datasets":[{"label":"Profit" if kind=="product_profit" else "Margin %","data":[x["profit"] if kind=="product_profit" else x["profit_margin"]*100 for x in rows],"backgroundColor":"#8ecae6"}]}
    if kind in ("monthly_revenue","monthly_profit"):
        field="revenue" if kind=="monthly_revenue" else "profit"
        return {"type":"bar","title":"Monthly "+field,"labels":[x["month"] for x in a["monthly"]],"datasets":[{"label":field.title(),"data":[x[field] for x in a["monthly"]],"backgroundColor":"#5aa9e6"}]}
    if kind == "store_aov":
        rows=sorted(a["stores"],key=lambda x:x["aov"],reverse=True)
        return {"type":"bar","title":"Average order value by store","labels":[x["store_name"] for x in rows],"datasets":[{"label":"AOV","data":[x["aov"] for x in rows],"backgroundColor":"#8ecae6"}]}
    if kind == "region_orders":
        rows=sorted(a["regions"],key=lambda x:x["orders"],reverse=True)
        return {"type":"bar","title":"Completed orders by region","labels":[x["region"] for x in rows],"datasets":[{"label":"Orders","data":[x["orders"] for x in rows],"backgroundColor":["#2563eb","#16a34a","#f59e0b","#9333ea"]}]}
    if kind == "category_share":
        x=a["categories"][0]
        return {"type":"doughnut","title":"Top category revenue share","labels":[x["category"],"All other categories"],"datasets":[{"label":"Revenue share","data":[x["revenue"],a["kpis"]["revenue"]-x["revenue"]],"backgroundColor":["#2563eb","#d1d5db"]}]}
    if kind == "product_share":
        top=sum(x["revenue"] for x in a["top_products"][:3])
        return {"type":"doughnut","title":"Top 3 product revenue share","labels":["Top 3 products","All other revenue"],"datasets":[{"label":"Revenue","data":[top,a["kpis"]["revenue"]-top],"backgroundColor":["#2563eb","#d1d5db"]}]}
    if kind == "customers":
        return {"type":"bar","title":"Completed-order customers","labels":["Customers"],"datasets":[{"label":"Customers","data":[a["kpis"]["customers"]],"backgroundColor":"#5aa9e6"}]}
    if kind == "discount":
        return {"type":"bar","title":"Average discount","labels":["Completed sales"],"datasets":[{"label":"Discount %","data":[a["kpis"]["avg_discount"]*100],"backgroundColor":"#f59e0b"}]}
    if kind == "category_discount":
        rows=sorted(a["categories"],key=lambda x:x["avg_discount"],reverse=True)
        return {"type":"bar","title":"Average discount by category","labels":[x["category"] for x in rows],"datasets":[{"label":"Discount %","data":[x["avg_discount"]*100 for x in rows],"backgroundColor":"#f59e0b"}]}
    if kind == "quality":
        rows=[]
        for f in files():
            q=quality(load(f))
            for issue in q["issues"]:
                rows.append({"label":f"{f}: {issue['type']} — {issue['column']}", "count":issue["count"]})
        rows=sorted(rows,key=lambda x:x["count"],reverse=True)
        return {"type":"bar","title":"Detected data-quality findings","labels":[x["label"] for x in rows],"datasets":[{"label":"Affected records/cells","data":[x["count"] for x in rows],"backgroundColor":"#f59e0b"}]} if rows else None
    return None


def ask_llm(question):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        answer, kind = local_answer(question)
        return {"mode": "grounded-demo", "answer": answer, "evidence": "Computed from governed DataLens functions.", "chart": chart_for(kind) if kind else None}

    tools = [
        {"name": "get_kpi_summary", "description": "Return computed Nexa Retail KPI values.", "input_schema": {"type": "object", "properties": {}, "required": []}},
        {"name": "top_categories", "description": "Return categories ranked by computed revenue.", "input_schema": {"type": "object", "properties": {"n": {"type": "integer"}}, "required": []}},
        {"name": "top_products", "description": "Return products ranked by computed revenue.", "input_schema": {"type": "object", "properties": {"n": {"type": "integer"}}, "required": []}},
        {"name": "store_performance", "description": "Return computed store revenue and profit.", "input_schema": {"type": "object", "properties": {}, "required": []}},
        {"name": "monthly_trend", "description": "Return computed monthly revenue and profit.", "input_schema": {"type": "object", "properties": {}, "required": []}},
        {"name": "customer_summary", "description": "Return computed customer count and related KPIs.", "input_schema": {"type": "object", "properties": {}, "required": []}},
        {"name": "data_quality_report", "description": "Return raw-dataset data-quality findings.", "input_schema": {"type": "object", "properties": {}, "required": []}}
    ]
    messages = [{"role": "user", "content": question}]
    for _ in range(3):
        payload = {
            "model": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            "max_tokens": 700,
            "system": "You are DataLens, an evidence-first retail analytics assistant. Never invent numbers. Use tools for factual business metrics. Explain results clearly.",
            "tools": tools, "messages": messages
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode(),
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.load(resp)
        messages.append({"role": "assistant", "content": data.get("content", [])})
        uses = [x for x in data.get("content", []) if x.get("type") == "tool_use"]
        if not uses:
            txt = " ".join(x.get("text", "") for x in data.get("content", []) if x.get("type") == "text")
            _, kind = local_answer(question)
            return {"mode": "tool-assisted", "answer": txt, "evidence": "Answer grounded in governed DataLens tool results.", "chart": chart_for(kind) if kind else None}
        results = []
        for u in uses:
            results.append({"type": "tool_result", "tool_use_id": u["id"], "content": json.dumps(tool_result(u["name"], u.get("input", {})), default=json_default)})
        messages.append({"role": "user", "content": results})
    return {"mode": "error", "answer": "The model requested too many tool steps. Try a narrower question.", "evidence": "No final answer was produced.", "chart": None}


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send(self, 200, {"ok": True})

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        try:
            if path == "/api/files":
                return send(self, 200, {"files": files()})
            if path == "/api/explore":
                name = dict(x.split("=", 1) for x in self.path.split("?", 1)[1].split("&") if "=" in x).get("file", "") if "?" in self.path else ""
                return send(self, 200, {"file": name, **profile(load(name))})
            if path == "/api/quality":
                name = dict(x.split("=", 1) for x in self.path.split("?", 1)[1].split("&") if "=" in x).get("file", "") if "?" in self.path else ""
                return send(self, 200, {"file": name, **quality(load(name))})
            if path == "/api/analytics":
                return send(self, 200, analytics())
            return send(self, 404, {"error": "Route not found"})
        except Exception as e:
            return send(self, 422, {"error": str(e)})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or "{}")
            path = self.path.split("?", 1)[0]
            if path == "/api/clean":
                df = load(body["file"])
                cleaned, log = clean_df(df, body.get("operations", {}))
                return send(self, 200, {
                    "file": body["file"], "before": profile(df), "after": profile(cleaned),
                    "log": log, "preview_before": clean_preview(df), "preview_after": clean_preview(cleaned)
                })
            if path == "/api/transform":
                df = load(body["file"])
                out = apply_transform(df, body["spec"])
                return send(self, 200, {
                    "file": body["file"], "new_column": body["spec"].get("new_column"),
                    "before_columns": list(df.columns), "after_columns": list(out.columns),
                    "preview_before": clean_preview(df), "preview_after": clean_preview(out)
                })
            if path == "/api/ask":
                return send(self, 200, ask_llm(body.get("question", "")))
            return send(self, 404, {"error": "Route not found"})
        except Exception as e:
            return send(self, 422, {"error": str(e)})


