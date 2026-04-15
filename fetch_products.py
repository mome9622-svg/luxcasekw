#!/usr/bin/env python3
"""
Shopify Product Fetcher
Fetches all products from a Shopify store and displays them in an organized format.
"""

import json
import os
import sys
import urllib.request
import urllib.error

SHOP_URL = os.environ.get("SHOPIFY_STORE_URL", "luxcase-kw.myshopify.com")
ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-01"


def fetch_products():
    """Fetch all products from Shopify using pagination."""
    products = []
    url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/products.json?limit=250"

    while url:
        req = urllib.request.Request(
            url,
            headers={
                "X-Shopify-Access-Token": ACCESS_TOKEN,
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                batch = data.get("products", [])
                products.extend(batch)

                # Handle pagination via Link header
                link_header = response.headers.get("Link", "")
                url = parse_next_link(link_header)

                print(f"  جاري التحميل... تم جلب {len(products)} منتج حتى الآن")

        except urllib.error.HTTPError as e:
            print(f"خطأ HTTP: {e.code} - {e.reason}")
            body = e.read().decode()
            print(f"التفاصيل: {body}")
            break
        except urllib.error.URLError as e:
            print(f"خطأ في الاتصال: {e.reason}")
            break

    return products


def parse_next_link(link_header):
    """Parse the 'next' URL from Shopify's Link pagination header."""
    if not link_header:
        return None
    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' in part:
            url = part.split(";")[0].strip().strip("<>")
            return url
    return None


def format_price(variants):
    """Extract price range from product variants."""
    if not variants:
        return "غير محدد"
    prices = [float(v.get("price", 0)) for v in variants if v.get("price")]
    if not prices:
        return "غير محدد"
    min_p = min(prices)
    max_p = max(prices)
    currency = "KWD"
    if min_p == max_p:
        return f"{min_p:.3f} {currency}"
    return f"{min_p:.3f} – {max_p:.3f} {currency}"


def display_products(products):
    """Display products in an organized, readable format."""
    if not products:
        print("لم يتم العثور على أي منتجات.")
        return

    separator = "─" * 70

    print(f"\n{'═' * 70}")
    print(f"  متجر LuxCase KW — إجمالي المنتجات: {len(products)}")
    print(f"{'═' * 70}\n")

    # Group products by product_type
    by_type = {}
    for product in products:
        ptype = product.get("product_type") or "غير مصنف"
        by_type.setdefault(ptype, []).append(product)

    for ptype, items in sorted(by_type.items()):
        print(f"\n  [ {ptype} ] — {len(items)} منتج")
        print(f"  {separator}")

        for i, product in enumerate(items, 1):
            title       = product.get("title", "بدون عنوان")
            status      = product.get("status", "unknown")
            variants    = product.get("variants", [])
            options     = product.get("options", [])
            images      = product.get("images", [])
            vendor      = product.get("vendor", "—")
            handle      = product.get("handle", "")
            tags        = product.get("tags", "")
            inventory   = sum(
                v.get("inventory_quantity", 0) or 0 for v in variants
            )

            status_ar = {"active": "نشط", "draft": "مسودة", "archived": "مؤرشف"}.get(
                status, status
            )
            price_str = format_price(variants)
            options_str = ", ".join(
                f"{o['name']} ({len(o.get('values', []))})"
                for o in options
            ) if options else "—"
            tags_str = tags if tags else "—"

            print(f"\n  {i:>3}. {title}")
            print(f"       الحالة    : {status_ar}")
            print(f"       السعر     : {price_str}")
            print(f"       المتوفر   : {inventory} وحدة")
            print(f"       المتغيرات : {len(variants)} | الخيارات: {options_str}")
            print(f"       الصور     : {len(images)}")
            print(f"       المورد    : {vendor}")
            print(f"       الوسوم    : {tags_str}")
            print(f"       الرابط    : https://{SHOP_URL}/products/{handle}")

        print(f"\n  {separator}")

    # Summary statistics
    total_active   = sum(1 for p in products if p.get("status") == "active")
    total_draft    = sum(1 for p in products if p.get("status") == "draft")
    total_archived = sum(1 for p in products if p.get("status") == "archived")
    total_variants = sum(len(p.get("variants", [])) for p in products)
    total_images   = sum(len(p.get("images", [])) for p in products)

    print(f"\n{'═' * 70}")
    print("  ملخص الإحصائيات:")
    print(f"  {'─' * 35}")
    print(f"  إجمالي المنتجات  : {len(products)}")
    print(f"  نشط              : {total_active}")
    print(f"  مسودة            : {total_draft}")
    print(f"  مؤرشف            : {total_archived}")
    print(f"  إجمالي المتغيرات : {total_variants}")
    print(f"  إجمالي الصور     : {total_images}")
    print(f"  عدد الفئات       : {len(by_type)}")
    print(f"{'═' * 70}\n")


def save_to_json(products, filename="products_export.json"):
    """Save the full product data to a JSON file for reference."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"  تم حفظ البيانات الكاملة في: {filename}")


if __name__ == "__main__":
    if not ACCESS_TOKEN:
        print("خطأ: يجب تعيين متغير البيئة SHOPIFY_ACCESS_TOKEN")
        print("مثال: export SHOPIFY_ACCESS_TOKEN='shpat_xxxx'")
        sys.exit(1)

    print(f"جاري الاتصال بمتجر: {SHOP_URL}")
    products = fetch_products()

    if products:
        display_products(products)
        save_to_json(products)
    else:
        print("لم يتم جلب أي منتجات. تحقق من الـ Access Token ورابط المتجر.")
