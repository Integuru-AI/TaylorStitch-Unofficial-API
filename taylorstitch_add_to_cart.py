from curl_cffi import requests
import os
import re
import uuid


def run(headers, user_input):
    """Add a product to the user's cart by SKU (variant SKU from list_new_arrivals)."""
    base_url = APP_URL

    sku = user_input.get("sku")
    if not sku:
        return {"status_code": 400, "body": {"error": "sku is required"}}

    quantity = user_input.get("quantity", 1)
    if not isinstance(quantity, int) or quantity < 1:
        return {"status_code": 400, "body": {"error": "quantity must be a positive integer"}}

    # Look up variant_id from SKU via Tagalys API
    variant_id = _resolve_variant_id(sku)
    if not variant_id:
        return {"status_code": 404, "body": {"error": f"SKU not found: {sku}"}}

    req_headers = {
        **headers,
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.taylorstitch.com",
    }

    # Step 1: Add to cart
    payload = {
        "items": [
            {
                "quantity": quantity,
                "id": str(variant_id),
                "properties": {
                    "_Phase": "retail",
                    "_fitFinderAssisted": "false",
                },
            }
        ]
    }

    response = requests.post(
        f"{base_url}/cart/add.js",
        json=payload,
        headers=req_headers,
        impersonate="chrome131",
        timeout=30,
    )

    # Detect expired session
    if response.status_code == 401 or "/account/login" in str(response.url):
        return {"status_code": 401, "body": {"error": "Session expired"}}

    if response.status_code != 200:
        return {"status_code": response.status_code, "body": {"error": "Failed to add item to cart", "details": response.text[:500]}}

    add_result = response.json()

    # Step 2: Get updated cart state
    cart_response = requests.get(
        f"{base_url}/cart.json",
        headers=req_headers,
        impersonate="chrome131",
        timeout=30,
    )

    if cart_response.status_code != 200:
        # Cart add succeeded but sync will fail - still return success
        return _format_response(add_result, synced=False)

    cart_data = cart_response.json()

    # Step 3: Get customer info and sync persistent cart
    customer_info = _get_customer_info(base_url, headers)
    if customer_info:
        _sync_persistent_cart(base_url, headers, cart_data, customer_info)

    return _format_response(add_result, synced=bool(customer_info))


# === PRIVATE ===


def _format_response(add_result, synced=False):
    """Format the add-to-cart response."""
    added_items = []
    for item in add_result.get("items", []):
        added_items.append({
            "variant_id": str(item.get("variant_id", "")),
            "sku": item.get("sku", ""),
            "title": item.get("title", ""),
            "quantity": item.get("quantity", 0),
            "price": item.get("price", 0) / 100.0,
        })

    return {
        "status_code": 200,
        "body": {
            "added_items": added_items,
            "synced": synced,
        },
    }


def _get_customer_info(base_url, headers):
    """Extract customer ID and email from an authenticated page."""
    response = requests.get(
        f"{base_url}/account",
        headers={
            **headers,
            "Accept": "text/html",
        },
        impersonate="chrome131",
        timeout=30,
    )

    if response.status_code != 200:
        return None

    # Extract customer ID from page meta: {"customerId":6843434139725}
    id_match = re.search(r'"customerId"\s*:\s*(\d+)', response.text)
    email_match = re.search(r'"email"\s*:\s*"([^"]+)"', response.text)

    if id_match and email_match:
        return {
            "id": id_match.group(1),
            "email": email_match.group(1),
        }

    return None


def _sync_persistent_cart(base_url, headers, cart_data, customer_info):
    """Sync the cart state to the persistent cart service for cross-session persistence."""
    sync_payload = {
        "customerID": customer_info["id"],
        "customerEmail": customer_info["email"],
        "shopifyCart": cart_data,
        "shopifyDomain": "taylor-stitch.myshopify.com",
        "localID": str(uuid.uuid4()),
    }

    requests.post(
        f"{base_url}/apps/cff-persistent-cart/customer-cart",
        json=sync_payload,
        headers={
            **headers,
            "Content-Type": "application/json",
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://www.taylorstitch.com",
        },
        impersonate="chrome131",
        timeout=30,
    )


def _resolve_variant_id(sku):
    """Resolve a SKU string to a Shopify variant ID using the Tagalys API."""
    tagalys_url = "https://api-r3.tagalys.com/v2/collections/181884740"

    params = {
        "include[]": ["products"],
        "page": 1,
        "per_page": 100,
        "sort": "trending",
        "collectionId": "181884740",
        "country": "US",
        "shop_id": "taylor-stitch.myshopify.com",
        "storefront_api_key": os.environ.get("TAGALYS_STOREFRONT_API_KEY", "YOUR_TAGALYS_STOREFRONT_API_KEY"),
    }

    response = requests.get(
        tagalys_url,
        params=params,
        headers={
            "Accept": "application/json",
            "Referer": "https://www.taylorstitch.com/",
        },
        timeout=30,
    )

    if response.status_code != 200:
        return None

    data = response.json()

    for product in data.get("products", []):
        for variant in product.get("variants", []):
            if variant.get("sku") == sku:
                return variant.get("id")

    return None
