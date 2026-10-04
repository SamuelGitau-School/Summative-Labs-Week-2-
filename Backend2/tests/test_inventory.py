import pytest

import data

NEW_ITEM = {"name": "Kettle", "category": "Kitchen", "price": 30, "stock": 2}


# ----------------------- everything needs a login --------------------------

@pytest.mark.parametrize("method, url", [
    ("get", "/inventory"),
    ("get", "/inventory/1"),
    ("post", "/inventory"),
    ("patch", "/inventory/1"),
    ("delete", "/inventory/1"),
    ("get", "/inventory/lookup?name=milk"),
    ("post", "/inventory/1/enrich"),
])
def test_routes_require_login(client, method, url):
    r = getattr(client, method)(url, json={})
    assert r.status_code == 401
    assert r.get_json()["error"] == "Please sign in."


# ------------------------------- read --------------------------------------

def test_list_returns_seed_items_with_owner(demo):
    items = demo.get("/inventory").get_json()
    assert [i["name"] for i in items] == ["Ceramic pour-over set", "Linen apron", "Brass desk lamp"]
    assert all(i["user_id"] == 1 and i["added_by"] == data.DEMO_EMAIL for i in items)


def test_get_one(demo):
    r = demo.get("/inventory/2")
    assert r.status_code == 200
    assert r.get_json()["name"] == "Linen apron"


@pytest.mark.parametrize("url", ["/inventory/99", "/inventory/abc", "/inventory/0"])
def test_get_unknown_is_404_json(demo, url):
    r = demo.get(url)
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_trailing_slash_works(demo):
    assert demo.get("/inventory/").status_code == 200


def test_wrong_method_is_405_json(demo):
    r = demo.put("/inventory/1", json={})
    assert r.status_code == 405
    assert r.get_json()["error"] == "Method not allowed."


def test_everyone_can_read_everything(make_user, demo):
    alice = make_user()
    assert len(alice.get("/inventory").get_json()) == 3
    assert alice.get("/inventory/1").status_code == 200


# ------------------------------ create -------------------------------------

def test_create_stamps_user_id_from_session(make_user):
    alice = make_user()
    r = alice.post("/inventory", json=NEW_ITEM)
    assert r.status_code == 201
    body = r.get_json()
    assert body["user_id"] == 2 and body["added_by"] == "alice@example.com"
    assert r.headers["Location"] == f"/inventory/{body['id']}"


def test_create_ignores_user_id_in_request_body(make_user):
    alice = make_user()
    r = alice.post("/inventory", json={**NEW_ITEM, "user_id": 1})
    assert r.get_json()["user_id"] == 2


def test_create_cleans_fields(demo):
    r = demo.post("/inventory", json={"name": "  Mug ", "category": " Kitchen", "price": 5, "stock": 1})
    body = r.get_json()
    assert body["name"] == "Mug" and body["category"] == "Kitchen"
    assert isinstance(body["price"], float)


def test_create_accepts_optional_barcode(demo):
    r = demo.post("/inventory", json={**NEW_ITEM, "barcode": "3274080005003"})
    assert r.status_code == 201 and r.get_json()["barcode"] == "3274080005003"


@pytest.mark.parametrize("changes, fragment", [
    ({"name": ""}, "name"),
    ({"name": "   "}, "name"),
    ({"name": 5}, "name"),
    ({"category": ""}, "category"),
    ({"price": -1}, "price"),
    ({"price": "12"}, "price"),
    ({"price": True}, "price"),
    ({"stock": 1.5}, "stock"),
    ({"stock": -3}, "stock"),
    ({"stock": False}, "stock"),
    ({"barcode": "12ab"}, "barcode"),
    ({"barcode": "123"}, "barcode"),
])
def test_create_rejects_bad_values(demo, changes, fragment):
    r = demo.post("/inventory", json={**NEW_ITEM, **changes})
    assert r.status_code == 400
    assert fragment in r.get_json()["error"]


@pytest.mark.parametrize("missing", ["name", "category", "price", "stock"])
def test_create_requires_every_field(demo, missing):
    body = {k: v for k, v in NEW_ITEM.items() if k != missing}
    r = demo.post("/inventory", json=body)
    assert r.status_code == 400
    assert r.get_json()["error"] == f"{missing} is required."


def test_create_non_object_body(demo):
    assert demo.post("/inventory", json=[1, 2]).status_code == 400
    assert demo.post("/inventory", data="hi").status_code == 400


def test_ids_are_never_reused(demo):
    first = demo.post("/inventory", json=NEW_ITEM).get_json()["id"]
    demo.delete(f"/inventory/{first}")
    second = demo.post("/inventory", json=NEW_ITEM).get_json()["id"]
    assert second == first + 1


# ------------------------------ update -------------------------------------

def test_patch_changes_only_sent_fields(demo):
    r = demo.patch("/inventory/1", json={"stock": 10})
    body = r.get_json()
    assert r.status_code == 200
    assert body["stock"] == 10 and body["name"] == "Ceramic pour-over set"


def test_patch_cannot_change_id_or_owner(make_user):
    alice = make_user()
    item_id = alice.post("/inventory", json=NEW_ITEM).get_json()["id"]
    r = alice.patch(f"/inventory/{item_id}", json={"id": 50, "user_id": 1, "name": "Renamed"})
    body = r.get_json()
    assert body["id"] == item_id and body["user_id"] == 2 and body["name"] == "Renamed"


@pytest.mark.parametrize("body", [{}, {"price": -5}, {"price": "x"}, {"stock": 2.5}, {"name": " "}, {"barcode": "abc"}])
def test_patch_rejects_bad_bodies(demo, body):
    assert demo.patch("/inventory/1", json=body).status_code == 400


def test_patch_non_object_body(demo):
    assert demo.patch("/inventory/1", json=[1]).status_code == 400


def test_patch_missing_item(demo):
    assert demo.patch("/inventory/99", json={"stock": 1}).status_code == 404


# ------------------------------ delete -------------------------------------

def test_delete_removes_item(demo):
    assert demo.delete("/inventory/1").status_code == 204
    assert demo.get("/inventory/1").status_code == 404
    assert len(demo.get("/inventory").get_json()) == 2


def test_delete_missing_item(demo):
    assert demo.delete("/inventory/99").status_code == 404


# ----------------------------- ownership -----------------------------------

def test_only_owner_can_patch_delete_or_enrich(make_user):
    alice = make_user()
    for call in (
        lambda: alice.patch("/inventory/1", json={"stock": 1}),
        lambda: alice.delete("/inventory/1"),
        lambda: alice.post("/inventory/1/enrich", json={}),
    ):
        r = call()
        assert r.status_code == 403
        assert r.get_json()["error"] == "You can only change items you added."
    assert data.find_item(1)["stock"] == 14  # untouched


def test_owner_can_change_own_item(make_user):
    alice = make_user()
    item_id = alice.post("/inventory", json=NEW_ITEM).get_json()["id"]
    assert alice.patch(f"/inventory/{item_id}", json={"stock": 9}).status_code == 200
    assert alice.delete(f"/inventory/{item_id}").status_code == 204


def test_missing_item_is_404_before_ownership(make_user):
    assert make_user().delete("/inventory/99").status_code == 404
