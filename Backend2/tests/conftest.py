import pytest

import data
from app import app as flask_app


@pytest.fixture(autouse=True)
def fresh_data():
    """Every test starts from the same seeded data (demo user + 3 items)."""
    data.reset()
    yield
    data.reset()


@pytest.fixture
def client():
    return flask_app.test_client()


def _login(client, email, password):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.get_json()
    return client


@pytest.fixture
def demo(client):
    """A client already logged in as the demo user (owner of the 3 seed items)."""
    return _login(client, data.DEMO_EMAIL, data.DEMO_PASSWORD)


@pytest.fixture
def make_user():
    """Factory: register a new user and return a logged-in client for them."""
    def make(email="alice@example.com", password="secret12"):
        c = flask_app.test_client()
        r = c.post("/auth/register", json={"email": email, "password": password, "confirm_password": password})
        assert r.status_code == 201, r.get_json()
        return c
    return make


class FakeResponse:
    """Stands in for a `requests` response."""
    def __init__(self, status_code=200, body=None, bad_json=False):
        self.status_code, self._body, self._bad_json = status_code, body, bad_json

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        if self._bad_json:
            raise ValueError("not json")
        return self._body


FOUND = {"status": 1, "product": {
    "code": "3274080005003", "product_name": "Spring water", "brands": "Cristaline",
    "quantity": "1.5 L", "categories": "Waters", "ingredients_text": "Eau de source",
    "nutriscore_grade": "a", "image_url": "https://example.com/water.jpg"}}
NOT_FOUND = {"status": 0, "status_verbose": "product not found"}
SEARCH = {"count": 2, "products": [
    {"code": "111111111111", "product_name": "Oat Milk", "brands": "Oatly", "quantity": "  ", "nutriscore_grade": "b"},
    {"code": "222222222222", "product_name": "Oat Drink", "brands": "Alpro"}]}


@pytest.fixture
def off(monkeypatch):
    """Replace the network call to Open Food Facts. Returns a recorder.

        off.reply(FakeResponse(200, FOUND))   # what the next calls return
        off.calls                              # list of (url, params)
    """
    class Recorder:
        def __init__(self):
            self.calls, self._reply, self._raise = [], FakeResponse(200, FOUND), None

        def reply(self, response):
            self._reply, self._raise = response, None

        def fail(self, exc):
            self._raise = exc

        def __call__(self, url, params=None, **kwargs):
            self.calls.append((url, params))
            if self._raise:
                raise self._raise
            return self._reply

    rec = Recorder()
    monkeypatch.setattr("off_client.requests.get", rec)
    return rec
