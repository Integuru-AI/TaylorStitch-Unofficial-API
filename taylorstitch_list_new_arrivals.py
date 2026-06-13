import os

from curl_cffi import requests


def run(headers, user_input):
    """Fetch new arrivals from Taylor Stitch with SKU, name, size, and price details."""
    try:
        data = _fetch_new_arrivals()
    except Exception as e:
        return {"status_code": 500, "body": {"error": str(e)}}

    products = []
    for product in data.get("products", []):
        name = product.get("title", "")
        price = product.get("price")
        available = product.get("available", False)

        # Extract sizes with their SKUs
        sizes = []
        for variant in product.get("variants", []):
            sizes.append({
                "sku": variant.get("sku", ""),
                "size": variant.get("title", ""),
                "available": variant.get("available", False),
            })

        products.append({
            "product_id": str(product.get("id", "")),
            "name": name,
            "price": price,
            "available": available,
            "sizes": sizes,
        })

    return {
        "status_code": 200,
        "body": {
            "total_count": data.get("total_count", 0),
            "products": products,
        },
    }


# === PRIVATE ===


def _fetch_new_arrivals():
    """Fetch new arrivals data from the product discovery API."""
    tagalys_url = "https://api-r3.tagalys.com/v2/collections/181884740"

    params = {
        "include[]": ["product_ids", "products", "total_count"],
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
        raise Exception("Failed to fetch new arrivals")

    return response.json()
