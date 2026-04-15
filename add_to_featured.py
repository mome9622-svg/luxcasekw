#!/usr/bin/env python3
"""
Add a product to the Featured Products collection on Shopify.

Usage:
    export SHOPIFY_ACCESS_TOKEN='shpat_xxxx'
    python3 add_to_featured.py
"""

import json
import os
import sys
import urllib.request
import urllib.error

SHOP_URL    = os.environ.get("SHOPIFY_STORE_URL", "luxcase-kw.myshopify.com")
ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-01"
PRODUCT_ID  = 10213396283713


# ── helpers ────────────────────────────────────────────────────────────────

def api_request(method: str, path: str, payload: dict | None = None):
    """Send a Shopify Admin API request and return the parsed JSON body."""
    url  = f"https://{SHOP_URL}/admin/api/{API_VERSION}/{path}"
    data = json.dumps(payload).encode() if payload else None

    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "X-Shopify-Access-Token": ACCESS_TOKEN,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code} {e.reason}")
        try:
            errors = json.loads(body)
            print(f"  تفاصيل الخطأ: {json.dumps(errors, ensure_ascii=False, indent=2)}")
        except Exception:
            print(f"  الرد الخام: {body}")
        raise


# ── step 1: find the Featured Products collection ─────────────────────────

def find_featured_collection() -> dict | None:
    """
    Search custom collections and smart collections for one whose title
    contains 'featured' (case-insensitive).  Returns the first match or None.
    """
    for endpoint in ("custom_collections", "smart_collections"):
        resp = api_request("GET", f"{endpoint}.json?limit=250")
        collections = resp.get(endpoint.replace("_collections", "_collections"), [])

        # The key in the response mirrors the endpoint name exactly
        collections = resp.get(endpoint, [])

        for col in collections:
            if "featured" in col.get("title", "").lower():
                col["_type"] = endpoint  # tag for display
                return col

    return None


def list_all_collections():
    """Print all available collections to help the user debug."""
    print("\n  قائمة جميع الـ Collections المتاحة:")
    print("  " + "─" * 55)
    for endpoint in ("custom_collections", "smart_collections"):
        resp  = api_request("GET", f"{endpoint}.json?limit=250")
        items = resp.get(endpoint, [])
        kind  = "Custom" if endpoint == "custom_collections" else "Smart"
        for col in items:
            print(f"  [{kind:6}] ID: {col['id']:<14}  {col['title']}")
    print()


# ── step 2: check if product is already in the collection ─────────────────

def already_in_collection(collection_id: int, product_id: int) -> bool:
    resp = api_request(
        "GET",
        f"collects.json?collection_id={collection_id}&product_id={product_id}",
    )
    return len(resp.get("collects", [])) > 0


# ── step 3: add the product via a Collect object ──────────────────────────

def add_product_to_collection(collection_id: int, product_id: int) -> dict:
    resp = api_request(
        "POST",
        "collects.json",
        {"collect": {"product_id": product_id, "collection_id": collection_id}},
    )
    return resp.get("collect", {})


# ── step 4: verify — fetch product titles in the collection ───────────────

def get_product_title(product_id: int) -> str:
    try:
        resp = api_request("GET", f"products/{product_id}.json?fields=id,title")
        return resp.get("product", {}).get("title", str(product_id))
    except Exception:
        return str(product_id)


# ── main ──────────────────────────────────────────────────────────────────

def main():
    if not ACCESS_TOKEN:
        print("خطأ: قم بتعيين متغير البيئة SHOPIFY_ACCESS_TOKEN أولاً.")
        print("  export SHOPIFY_ACCESS_TOKEN='shpat_xxxx'")
        sys.exit(1)

    separator = "─" * 60
    print(f"\n{'═' * 60}")
    print(f"  Shopify → إضافة منتج إلى مجموعة Featured Products")
    print(f"{'═' * 60}")
    print(f"  المتجر    : {SHOP_URL}")
    print(f"  المنتج    : {PRODUCT_ID}")
    print()

    # 1. جلب عنوان المنتج
    print("[ 1/4 ] جلب بيانات المنتج...")
    product_title = get_product_title(PRODUCT_ID)
    print(f"        المنتج: {product_title} (ID: {PRODUCT_ID})")

    # 2. البحث عن مجموعة Featured Products
    print("\n[ 2/4 ] البحث عن مجموعة 'Featured Products'...")
    collection = find_featured_collection()

    if not collection:
        print("  لم يتم العثور على مجموعة باسم 'Featured Products'.")
        list_all_collections()
        print("  استخدم معرّف (ID) المجموعة المناسبة وعدّل COLLECTION_ID في السكريبت.")
        sys.exit(1)

    col_id    = collection["id"]
    col_title = collection["title"]
    col_type  = collection.get("_type", "")
    print(f"        تم الإيجاد: {col_title} (ID: {col_id}, النوع: {col_type})")

    # 3. التحقق من عدم وجود المنتج مسبقاً
    print("\n[ 3/4 ] التحقق من الحالة الحالية...")
    if already_in_collection(col_id, PRODUCT_ID):
        print(f"        المنتج '{product_title}' موجود بالفعل في '{col_title}'.")
        print(f"\n{'═' * 60}")
        print("  لا يلزم اتخاذ أي إجراء.")
        print(f"{'═' * 60}\n")
        sys.exit(0)
    else:
        print("        المنتج غير موجود في المجموعة — سيتم إضافته.")

    # 4. الإضافة الفعلية
    print("\n[ 4/4 ] إضافة المنتج إلى المجموعة...")
    collect = add_product_to_collection(col_id, PRODUCT_ID)
    collect_id = collect.get("id")

    print(f"\n{'═' * 60}")
    print("  تمت الإضافة بنجاح!")
    print(f"  {separator}")
    print(f"  Collect ID   : {collect_id}")
    print(f"  المنتج       : {product_title} (ID: {PRODUCT_ID})")
    print(f"  المجموعة     : {col_title} (ID: {col_id})")
    print(f"  رابط المتجر  : https://{SHOP_URL}/collections/{collection.get('handle', '')}")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
