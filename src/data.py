import csv
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent

def _read(name):
    with (DATA / name).open(encoding = "utf-8", newline = "") as f:
        return list(csv.DictReader(f))
_PRODUCTS = {r["sku"]: r for r in _read(DATA / "Capstone_Project_Dataset_FTTT_2026" / "data" / "products.csv")}
_PINCODES = {r["pincode"]: r for r in _read(DATA / "Capstone_Project_Dataset_FTTT_2026" / "data" / "pincodes.csv")}
_HOLIDAYS = {r["date"] for r in _read(DATA / "Capstone_Project_Dataset_FTTT_2026" / "data" / "holidays.csv")}

def _b(v: str) -> bool:
    return v == "True"

#product
def get_product(sku: str) -> dict:
    row = _PRODUCTS.get(str(sku).strip())
    if not row:
        return {"found":False, "sku": sku}
    assured = _b(row["assured"])
    return {
        "found" : True,
        "sku" : row["sku"],
        "title" : row["title"],
        "brand" : row["brand"],
        "return_category" : row["return_category"],
        "price_inr" : int(row["price_inr"]),
        "fulfilled_by" : row["fullfilled_by"],
        "assured" : assured,
        "assured_applies": assured and row["fulfilled_by"] == "ZentroMart",
        "warranty_months": int(row["warranty_months"])

    }

def search_products(query: str, limit: int = 3):
    q = query.lower().strip()
    if not q:
        return {"hits" : [], "count" : 0}
    hits = []
    for row in _PRODUCTS.values():
        if q in row["title"].lower() or q in row["brand"].lower():
            hits.append({k: row[k] for k in ("sku", "title", "return_category", "price_inr", "assured", "fulfilled_by")})

    return {"hits" : hits[:limit], "count": len(hits)}





def check_pincode(pincode: str) -> dict:
    row = _PINCODES.get(str(pincode).strip())
    if not row:
        return {"found": False, "pincode":pincode, "serviceable":False, "messages": "Pincode is not in ZentroMart's serviceable list"}

    return {
        "found": True,
        "pincode": row["pincode"],
        "city": row["city"], 
        "state": row["state"],
        "serviceable": _b(row["serviceable"]),
        "cod_available": _b(row["cod_available"]),
        "express_available": _b(row["express_available"]),
        "metro": _b(row["metro"])
    }   

#business day
def _is_business_day(d: date) -> bool:
    return d.weekday() < 6 and d.isoformat() not in _HOLIDAYS

def add_business_days(start_iso: str, n: int) -> str:
    d = date.fromisoformat(start_iso)
    added = 0
    while added < n:
        d= d + timedelta(days = 1)
        if _is_business_day(d):
            added = added + 1
    return d.isoformat()

def business_days_between(start_iso: str, end_iso: str) -> int:
    s, e = date.fromisoformat(start_iso), date.fromisoformat(end_iso)
    if e <= s:
        return 0
    n = 0
    while s < e:
        s += timedelta(days=1)
        if _is_business_day(s):
            n += 1
    return n

