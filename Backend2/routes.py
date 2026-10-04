from flask import Blueprint, jsonify, request, session

import data
import off_client
from auth import require_login
from off_client import ExternalAPIError
from validation import validate

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")
inventory_bp.before_request(require_login)  # every route below needs a logged-in user


def not_found():
    return jsonify(error="Item not found."), 404


def present(item):
    """The item plus the email of whoever added it."""
    owner = data.find_user(item["user_id"])
    return {**item, "added_by": owner["email"] if owner else "unknown"}


def get_owned(item_id):
    """Returns (item, None) if it exists and the logged-in user added it,
    otherwise (None, error_response)."""
    item = data.find_item(item_id)
    if not item:
        return None, not_found()
    if item["user_id"] != session["user_id"]:
        return None, (jsonify(error="You can only change items you added."), 403)
    return item, None


# ------------------------------ CRUD ---------------------------------------

@inventory_bp.get("")
def get_all():
    return jsonify([present(item) for item in data.inventory])


@inventory_bp.get("/<int:item_id>")
def get_one(item_id):
    item = data.find_item(item_id)
    return jsonify(present(item)) if item else not_found()


@inventory_bp.post("")
def create():
    fields, error = validate(request.get_json(silent=True))
    if error:
        return jsonify(error=error), 400
    item = data.add_item(fields, session["user_id"])  # user_id comes from the session, not the request
    return jsonify(present(item)), 201, {"Location": f"/inventory/{item['id']}"}


@inventory_bp.patch("/<int:item_id>")
def update(item_id):
    item, problem = get_owned(item_id)
    if problem:
        return problem
    fields, error = validate(request.get_json(silent=True), partial=True)
    if error:
        return jsonify(error=error), 400
    item.update(fields)
    return jsonify(present(item))


@inventory_bp.delete("/<int:item_id>")
def delete(item_id):
    item, problem = get_owned(item_id)
    if problem:
        return problem
    data.inventory.remove(item)
    return "", 204


# ------------------------ Open Food Facts ----------------------------------

@inventory_bp.get("/lookup")
def lookup():
    """Preview OFF results without saving anything: ?barcode=... or ?name=.."""
    barcode = request.args.get("barcode", "").strip()
    name = request.args.get("name", "").strip()
    if not barcode and not name:
        return jsonify(error="Provide a barcode or a name."), 400
    if barcode and not off_client.is_barcode(barcode):
        return jsonify(error="barcode must be 8 to 14 digits."), 400

    try:
        results = off_client.lookup(barcode or name)
    except ExternalAPIError as e:
        return jsonify(error=str(e)), 502
    return jsonify(results)


@inventory_bp.post("/<int:item_id>/enrich")
def enrich(item_id):
    """Fetch details from OFF and store them on the item under "details".

    Searches by, in order: a barcode or name in the request body, the item's
    saved barcode, the item's name.
    """
    item, problem = get_owned(item_id)
    if problem:
        return problem

    body = request.get_json(silent=True) or {}
    query = (str(body.get("barcode") or "").strip()
             or str(body.get("name") or "").strip()
             or item.get("barcode")
             or item["name"])

    try:
        results = off_client.lookup(query)
    except ExternalAPIError as e:
        return jsonify(error=str(e)), 502
    if not results:
        return jsonify(error="No matching product found on Open Food Facts."), 404

    details = results[0]
    item["details"] = details
    if not item.get("barcode") and details["barcode"]:
        item["barcode"] = details["barcode"]
    return jsonify(present(item))
