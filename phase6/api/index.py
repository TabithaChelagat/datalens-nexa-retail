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
    monthly = completed.groupby("month", dropna=True).agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index().tail(24)
    by_store = completed.groupby("store_id").agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index().merge(s, on="store_id", how="left").sort_values("revenue", ascending=False).head(10)
    by_cat = completed.groupby("category").agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index().sort_values("revenue", ascending=False)
    top_products = completed.groupby(["product_id", "product_name"]).agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index().sort_values("revenue", ascending=False).head(10)
    return {
        "kpis": {"revenue": revenue, "profit": profit, "orders": orders, "customers": customers,
                 "aov": revenue / orders if orders else 0, "profit_margin": profit / revenue if revenue else 0},
        "monthly": monthly.to_dict("records"), "stores": by_store.to_dict("records"),
        "categories": by_cat.to_dict("records"), "top_products": top_products.to_dict("records")
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
    q = question.lower()
    if ("store" in q) and ("perform" in q or "better" in q or "revenue" in q or "profit" in q):
        rows = a["stores"][:5]
        return "Store performance by revenue: " + "; ".join(f"{r.get('store_name', r['store_id'])} — revenue {r['revenue']:.2f}, profit {r['profit']:.2f}" for r in rows), "stores"
    if "customer" in q and ("how many" in q or "count" in q or "number" in q):
        return f"There are {a['kpis']['customers']:,} customers associated with completed orders in the governed analytics dataset.", "customers"
    if ("trend" in q or "monthly" in q) and ("revenue" in q or "profit" in q or "sales" in q):
        return "The monthly revenue/profit trend is shown in the chart and table below.", "trend"
    if ("top" in q or "highest" in q or "best" in q) and "categor" in q:
        return "Top categories by revenue: " + ", ".join(f"{x['category']} ({x['revenue']:.2f})" for x in a["categories"][:3]), "categories"
    if ("top" in q or "highest" in q or "best" in q) and "product" in q:
        return "Top products by revenue: " + ", ".join(f"{x['product_name']} ({x['revenue']:.2f})" for x in a["top_products"][:3]), "products"
    if "margin" in q:
        return f"Overall profit margin is {a['kpis']['profit_margin']:.1%}, based on computed revenue and profit.", "margin"
    if "quality" in q or "issue" in q:
        total = sum(quality(load(f))["issue_count"] for f in files())
        return f"The raw demo files contain {total} detected issue type(s). Use the Data Quality stage for the file-level findings and counts.", "quality"
    if "revenue" in q or "profit" in q or "kpi" in q:
        return f"Revenue is {a['kpis']['revenue']:.2f}, profit is {a['kpis']['profit']:.2f}, with {a['kpis']['orders']} completed orders and AOV of {a['kpis']['aov']:.2f}.", "kpis"
    return "I can answer questions about revenue, profit, margin, stores, categories, products, customers, monthly trends and data quality using computed DataLens functions.", None


def chart_for(kind):
    a = analytics()
    if kind == "stores":
        rows = a["stores"][:10]
        return {"type": "bar", "title": "Revenue by store", "labels": [r.get("store_name", r["store_id"]) for r in rows],
                "datasets": [{"label": "Revenue", "data": [r["revenue"] for r in rows]}]}
    if kind == "categories":
        rows = a["categories"]
        return {"type": "bar", "title": "Revenue by category", "labels": [r["category"] for r in rows],
                "datasets": [{"label": "Revenue", "data": [r["revenue"] for r in rows]}]}
    if kind == "products":
        rows = a["top_products"]
        return {"type": "bar", "title": "Top products by revenue", "labels": [r["product_name"] for r in rows],
                "datasets": [{"label": "Revenue", "data": [r["revenue"] for r in rows]}]}
    if kind == "trend":
        rows = a["monthly"]
        return {"type": "line", "title": "Monthly revenue and profit", "labels": [r["month"] for r in rows],
                "datasets": [{"label": "Revenue", "data": [r["revenue"] for r in rows]},
                             {"label": "Profit", "data": [r["profit"] for r in rows]}]}
    if kind == "margin":
        return {"type": "bar", "title": "Revenue vs profit", "labels": ["Revenue", "Profit"],
                "datasets": [{"label": "Amount", "data": [a["kpis"]["revenue"], a["kpis"]["profit"]]}]}
    if kind == "customers":
        return {"type": "bar", "title": "Customer count", "labels": ["Customers"], "datasets": [{"label": "Customers", "data": [a["kpis"]["customers"]]}]}
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


