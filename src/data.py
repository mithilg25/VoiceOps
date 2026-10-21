import csv
from datetime import date, timedelta
from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent / "data"

def _read(name):
    # Changed encoding to utf-8-sig to handle any invisible BOM characters in the CSV
    with (_DATA / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

_PRODUCTS = {r["sku"]: r for r in _read("products.csv")}
_PINCODES = {r["pincode"]: r for r in _read("pincodes.csv")}
_HOLIDAYS = {r["date"] for r in _read("holidays.csv")}

def _b(v: str) -> bool:
    return str(v).strip().lower() == "true"

def get_product(sku: str) -> dict:
    row = _PRODUCTS.get(str(sku).strip().upper())
    if not row:
        return {"found": False, "sku": sku}
    return {
        "found": True, 
        "sku": row.get("sku", ""), 
        "title": row.get("title", ""),
        "return_category": row.get("return_category", ""), 
        "price_inr": int(row.get("price_inr", 0) or 0),
        "fulfilled_by": row.get("fulfilled_by", ""), 
        "assured": _b(row.get("assured", "False")),
        "warranty_months": int(row.get("warranty_months", 0) or 0),
    }

def search_products(query: str, limit: int = 3) -> dict:
    q = query.lower().strip()
    if not q: return {"hits": [], "count": 0}
    hits = []
    for row in _PRODUCTS.values():
        if q in row.get("title", "").lower() or q in row.get("brand", "").lower():
            hits.append({
                "sku": row.get("sku", ""), "title": row.get("title", ""), 
                "return_category": row.get("return_category", ""), 
                "price_inr": row.get("price_inr", ""), "assured": row.get("assured", ""), 
                "fulfilled_by": row.get("fulfilled_by", "")
            })
    return {"hits": hits[:limit], "count": len(hits)}

def check_pincode(pincode: str) -> dict:
    row = _PINCODES.get(str(pincode).strip())
    if not row:
        return {"found": False, "pincode": pincode, "serviceable": False, "message": "Pincode not serviceable."}
    return {
        "found": True, "pincode": row.get("pincode", ""), "city": row.get("city", ""), "state": row.get("state", ""),
        "serviceable": _b(row.get("serviceable", "False")), 
        "cod_available": _b(row.get("cod_available", "False")),
        "express_available": _b(row.get("express_available", "False")),
    }

def _is_business_day(d: date) -> bool:
    return d.weekday() < 6 and d.isoformat() not in _HOLIDAYS

def add_business_days(start_iso: str, n: int) -> str:
    if not start_iso or n < 0: return start_iso
    d = date.fromisoformat(start_iso)
    added = 0
    while added < n:
        d += timedelta(days=1)
        if _is_business_day(d):
            added += 1
    return d.isoformat()

def business_days_between(start_iso: str, end_iso: str) -> int:
    if not start_iso or not end_iso: return 0
    s, e = date.fromisoformat(start_iso), date.fromisoformat(end_iso)
    if e <= s: return 0
    n = 0
    while s < e:
        s += timedelta(days=1)
        if _is_business_day(s):
            n += 1
    return n