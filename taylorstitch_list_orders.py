from curl_cffi import requests
from bs4 import BeautifulSoup
import re


def run(headers, user_input):
    """Fetch all previous orders with product details (SKU/product ID, name, size, date)."""
    response = _fetch_account_page(headers)

    # Detect expired session (redirect to login page)
    if "/account/login" in str(response.url) or "Log in" in response.text[:5000]:
        return {"status_code": 401, "body": {"error": "Session expired"}}

    if response.status_code != 200:
        return {"status_code": response.status_code, "body": {"error": "Failed to load account page"}}

    soup = BeautifulSoup(response.text, "html.parser")

    orders = []
    order_sections = soup.find_all("div", class_="collection-scroller order-scroller")

    for section in order_sections:
        # Extract order date and number from heading
        heading = section.find("hgroup", class_="order-heading")
        if not heading:
            continue

        h2 = heading.find("h2")
        if not h2:
            continue

        date_span = h2.find("span", class_="pre-heading")
        order_date = date_span.get_text(strip=True) if date_span else ""

        # Order number is the text after the span inside h2
        order_number = h2.get_text(strip=True).replace(order_date, "").strip()

        # Extract products from this order
        items = section.find_all("figure", class_="product-card product-card--order")

        products = []
        seen_products = set()

        for item in items:
            product_id = item.get("data-product-card", "")

            # Get product name
            title_tag = item.find("b", class_="product-card__title")
            if title_tag:
                spans = title_tag.find_all("span", recursive=False)
                name_parts = []
                for span in spans:
                    text = span.get_text(strip=True)
                    # Fix missing space: "inDark Brown" -> "in Dark Brown"
                    if text.startswith("in") and len(text) > 2 and text[2:3].isupper():
                        text = "in " + text[2:]
                    name_parts.append(text)
                name = " ".join(name_parts)
            else:
                name = ""

            # Get size
            desc_tag = item.find("p", class_="product-card__description")
            size = ""
            if desc_tag:
                size_text = desc_tag.get_text(strip=True)
                # Format is "Size: XL" or "Size: L - 42"
                if size_text.startswith("Size:"):
                    size = size_text.replace("Size:", "").strip()

            # Deduplicate items within same order (same product can appear in multiple cards linking to same order)
            dedup_key = f"{product_id}_{size}"
            if dedup_key in seen_products:
                continue
            seen_products.add(dedup_key)

            products.append({
                "sku": product_id,
                "name": name,
                "size": size,
            })

        if products:
            orders.append({
                "order_number": order_number,
                "date": order_date,
                "items": products,
            })

    return {"status_code": 200, "body": {"orders": orders}}


# === PRIVATE ===

def _fetch_account_page(headers):
    """Fetch the account page HTML."""
    base_url = APP_URL

    return requests.get(
        f"{base_url}/account",
        headers={
            **headers,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
        impersonate="chrome131",
        timeout=30,
    )
