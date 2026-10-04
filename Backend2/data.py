"""Temporary in-memory storage. Resets whenever the server restarts."""
from werkzeug.security import generate_password_hash

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "password123"

users = []
inventory = []
_next_user_id = 1
_next_id = 1  # item ids are never reused, even after a delete

_SEED_ITEMS = [
    ("Ceramic pour-over set", "Kitchen", 38.0, 14),
    ("Linen apron", "Kitchen", 24.0, 31),
    ("Brass desk lamp", "Office", 72.0, 6),
]


_DEMO_HASH = generate_password_hash(DEMO_PASSWORD)  # hashed once, reused by reset()


def _store_user(email, password_hash):
    global _next_user_id
    user = {"id": _next_user_id, "email": email.lower(), "password_hash": password_hash}
    _next_user_id += 1
    users.append(user)
    return user


def add_user(email, password):
    return _store_user(email, generate_password_hash(password))  # never store the plain password


def find_user(user_id):
    return next((u for u in users if u["id"] == user_id), None)


def find_user_by_email(email):
    return next((u for u in users if u["email"] == email.lower()), None)


def find_item(item_id):
    return next((item for item in inventory if item["id"] == item_id), None)


def add_item(fields, user_id):
    global _next_id
    item = {"id": _next_id, **fields, "user_id": user_id}  # user_id = who added it
    _next_id += 1
    inventory.append(item)
    return item


def reset():
    """Empty the store, then re-create the demo account and its starting items."""
    global _next_user_id, _next_id
    users.clear()
    inventory.clear()
    _next_user_id = 1
    _next_id = 1
    demo = _store_user(DEMO_EMAIL, _DEMO_HASH)
    for name, category, price, stock in _SEED_ITEMS:
        add_item({"name": name, "category": category, "price": price, "stock": stock}, demo["id"])


reset()  # seed on startup
