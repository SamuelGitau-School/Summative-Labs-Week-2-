import pytest
import requests

import off_client
from tests.conftest import FOUND, NOT_FOUND, SEARCH, FakeResponse


# --------------------------- the client itself -----------------------------

@pytest.mark.parametrize("text, expected", [
    ("3274080005003", True), ("12345678", True), ("12345678901234", True),
    ("1234567", False), ("123456789012345", False), ("abc12345678", False), ("", False), (None, False),
])
def test_is_barcode(text, expected):
    assert off_client.is_barcode(text) is expected


def test_fetch_by_barcode_shapes_the_product(off):
    details = off_client.fetch_by_barcode("3274080005003")
    assert details == {
        "barcode": "3274080005003", "product_name": "Spring water", "brands": "Cristaline",
        "quantity": "1.5 L", "categories": "Waters", "ingredients": "Eau de source",
        "nutriscore_grade": "a", "image_url": "https://example.com/water.jpg",
    }
    url, params = off.calls[0]
    assert url.endswith("/api/v2/product/3274080005003.json")
    assert "nutriscore_grade" in params["fields"]


def test_fetch_by_barcode_not_found_returns_none(off):
    off.reply(FakeResponse(404, NOT_FOUND))
    assert off_client.fetch_by_barcode("12345678") is None


def test_missing_and_blank_fields_become_none(off):
    off.reply(FakeResponse(200, SEARCH))
    first = off_client.search_by_name("oat")[0]
    assert first["quantity"] is None  # "  " is blank
    assert first["categories"] is None  # missing


def test_search_by_name_sends_terms_and_limit(off):
    off.reply(FakeResponse(200, SEARCH))
    results = off_client.search_by_name("oat milk", limit=3)
    assert [r["product_name"] for r in results] == ["Oat Milk", "Oat Drink"]
    _, params = off.calls[0]
    assert params["search_terms"] == "oat milk" and params["page_size"] == 3 and params["json"] == 1


def test_lookup_picks_barcode_or_name(off):
    off_client.lookup("3274080005003")
    assert "/api/v2/product/" in off.calls[-1][0]
    off.reply(FakeResponse(200, SEARCH))
    off_client.lookup("oat milk")
    assert "cgi/search.pl" in off.calls[-1][0]


def test_requests_identify_the_app_and_have_a_timeout(monkeypatch):
    seen = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        seen.update(headers=headers, timeout=timeout)
        return FakeResponse(200, FOUND)

    monkeypatch.setattr("off_client.requests.get", fake_get)
    off_client.fetch_by_barcode("3274080005003")
    assert "Stockroom" in seen["headers"]["User-Agent"]
    assert seen["timeout"] == off_client.TIMEOUT


@pytest.mark.parametrize("failure", [
    requests.Timeout(), requests.ConnectionError(),
])
def test_network_failures_become_external_api_error(off, failure):
    off.fail(failure)
    with pytest.raises(off_client.ExternalAPIError):
        off_client.lookup("oat milk")


@pytest.mark.parametrize("response", [FakeResponse(503, {}), FakeResponse(200, bad_json=True)])
def test_bad_responses_become_external_api_error(off, response):
    off.reply(response)
    with pytest.raises(off_client.ExternalAPIError):
        off_client.lookup("oat milk")


# ------------------------------ /lookup route ------------------------------

def test_lookup_by_barcode(demo, off):
    r = demo.get("/inventory/lookup?barcode=3274080005003")
    assert r.status_code == 200
    assert r.get_json()[0]["brands"] == "Cristaline"


def test_lookup_unknown_barcode_is_empty_list(demo, off):
    off.reply(FakeResponse(404, NOT_FOUND))
    r = demo.get("/inventory/lookup?barcode=12345678")
    assert r.status_code == 200 and r.get_json() == []


def test_lookup_by_name(demo, off):
    off.reply(FakeResponse(200, SEARCH))
    r = demo.get("/inventory/lookup?name=oat+milk")
    assert [p["brands"] for p in r.get_json()] == ["Oatly", "Alpro"]


def test_lookup_saves_nothing(demo, off):
    demo.get("/inventory/lookup?barcode=3274080005003")
    assert "details" not in demo.get("/inventory/1").get_json()


@pytest.mark.parametrize("query", ["", "?barcode=abc", "?barcode=123"])
def test_lookup_validates_input(demo, off, query):
    assert demo.get(f"/inventory/lookup{query}").status_code == 400
    assert off.calls == []  # never hit the network on bad input


def test_lookup_failure_is_502(demo, off):
    off.fail(requests.ConnectionError())
    r = demo.get("/inventory/lookup?name=milk")
    assert r.status_code == 502
    assert "Open Food Facts" in r.get_json()["error"]


# ----------------------------- /enrich route -------------------------------

def test_enrich_with_barcode_saves_details_and_barcode(demo, off):
    r = demo.post("/inventory/1/enrich", json={"barcode": "3274080005003"})
    body = r.get_json()
    assert r.status_code == 200
    assert body["details"]["brands"] == "Cristaline"
    assert body["barcode"] == "3274080005003"
    assert demo.get("/inventory/1").get_json()["details"]["nutriscore_grade"] == "a"  # persisted


def test_enrich_uses_saved_barcode(demo, off):
    demo.patch("/inventory/1", json={"barcode": "3274080005003"})
    demo.post("/inventory/1/enrich")
    assert off.calls[-1][0].endswith("/3274080005003.json")


def test_enrich_falls_back_to_item_name(demo, off):
    off.reply(FakeResponse(200, SEARCH))
    r = demo.post("/inventory/2/enrich")
    assert off.calls[-1][1]["search_terms"] == "Linen apron"
    assert r.get_json()["details"]["brands"] == "Oatly"
    assert r.get_json()["barcode"] == "111111111111"  # adopted from the best match


def test_enrich_keeps_existing_barcode(demo, off):
    demo.patch("/inventory/1", json={"barcode": "99999999"})
    off.reply(FakeResponse(200, FOUND))
    body = demo.post("/inventory/1/enrich", json={"barcode": "3274080005003"}).get_json()
    assert body["barcode"] == "99999999"


def test_enrich_no_match_is_404(demo, off):
    off.reply(FakeResponse(200, {"products": []}))
    r = demo.post("/inventory/1/enrich")
    assert r.status_code == 404
    assert "details" not in demo.get("/inventory/1").get_json()


def test_enrich_failure_is_502_and_changes_nothing(demo, off):
    off.fail(requests.Timeout())
    r = demo.post("/inventory/1/enrich")
    assert r.status_code == 502
    assert "details" not in demo.get("/inventory/1").get_json()


def test_enrich_missing_item(demo, off):
    assert demo.post("/inventory/99/enrich").status_code == 404
    assert off.calls == []
