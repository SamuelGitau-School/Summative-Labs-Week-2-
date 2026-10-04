"""Small client for the Open Food Facts API (free, no API key needed)."""
import re

import requests

BASE_URL = "https://world.openfoodfacts.org"
HEADERS = {"User-Agent": "Stockroom/1.0 (student project)"}  # OFF asks apps to identify themselves
TIMEOUT = 10  # seconds
FIELDS = "code,product_name,brands,quantity,categories,ingredients_text,nutriscore_grade,image_url"


class ExternalAPIError(Exception):
    """Open Food Facts could not be reached or returned something unusable."""


def is_barcode(text):
    """Barcodes (EAN/UPC) are 8 to 14 digits."""
    return isinstance(text, str) and re.fullmatch(r"\d{8,14}", text.strip()) is not None


def _get(url, params):
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        if response.status_code != 404:  # OFF answers 404 for unknown barcodes; handled by the caller
            response.raise_for_status()
        return response.json()
    except requests.Timeout:
        raise ExternalAPIError("Open Food Facts took too long to respond.")
    except (requests.RequestException, ValueError):
        raise ExternalAPIError("Could not get a valid response from Open Food Facts.")


def _shape(product):
    """Keep only the fields we store. Blank values become None."""
    def clean(key):
        value = product.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else None

    return {
        "barcode": clean("code"),
        "product_name": clean("product_name"),
        "brands": clean("brands"),
        "quantity": clean("quantity"),
        "categories": clean("categories"),
        "ingredients": clean("ingredients_text"),
        "nutriscore_grade": clean("nutriscore_grade"),
        "image_url": clean("image_url"),
    }


def fetch_by_barcode(barcode):
    """Return one product's details, or None if the barcode isn't in the database."""
    data = _get(f"{BASE_URL}/api/v2/product/{barcode.strip()}.json", {"fields": FIELDS})
    if data.get("status") != 1 or not data.get("product"):
        return None
    details = _shape(data["product"])
    details["barcode"] = details["barcode"] or barcode.strip()
    return details


def search_by_name(name, limit=5):
    """Return up to `limit` matching products (best match first)."""
    data = _get(
        f"{BASE_URL}/cgi/search.pl",
        {"search_terms": name, "search_simple": 1, "action": "process",
         "json": 1, "page_size": limit, "fields": FIELDS},
    )
    return [_shape(p) for p in data.get("products", [])]


def lookup(query):
    """Search by barcode if the text looks like one, otherwise by product name."""
    if is_barcode(query):
        product = fetch_by_barcode(query)
        return [product] if product else []
    return search_by_name(query)
