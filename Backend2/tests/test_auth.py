import pytest

import data

REGISTER = {"email": "alice@example.com", "password": "secret12", "confirm_password": "secret12"}


# ----------------------------- register ------------------------------------

def test_register_creates_account_and_signs_in(client):
    r = client.post("/auth/register", json=REGISTER)
    assert r.status_code == 201
    assert r.get_json()["user"]["email"] == "alice@example.com"
    assert client.get("/auth/me").get_json()["user"]["email"] == "alice@example.com"


def test_register_lowercases_and_trims_email(client):
    r = client.post("/auth/register", json={**REGISTER, "email": "  Alice@Example.COM "})
    assert r.get_json()["user"]["email"] == "alice@example.com"


def test_register_rejects_mismatched_confirmation(client):
    r = client.post("/auth/register", json={**REGISTER, "confirm_password": "different1"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "Passwords do not match."
    assert data.find_user_by_email("alice@example.com") is None


@pytest.mark.parametrize("confirm", [None, "", 12345])
def test_register_requires_confirmation(client, confirm):
    body = {**REGISTER, "confirm_password": confirm}
    if confirm is None:
        del body["confirm_password"]
    r = client.post("/auth/register", json=body)
    assert r.status_code == 400
    assert r.get_json()["error"] == "Please confirm your password."


@pytest.mark.parametrize("changes, message", [
    ({"email": "nope"}, "Enter a valid email address."),
    ({"email": ""}, "Enter a valid email address."),
    ({"email": 42}, "Enter a valid email address."),
    ({"password": "12345", "confirm_password": "12345"}, "Password must be at least 6 characters."),
    ({"password": None}, "Password must be at least 6 characters."),
])
def test_register_validation(client, changes, message):
    r = client.post("/auth/register", json={**REGISTER, **changes})
    assert r.status_code == 400
    assert r.get_json()["error"] == message


def test_register_non_json_body(client):
    r = client.post("/auth/register", data="hello")
    assert r.status_code == 400
    assert r.get_json()["error"] == "Request body must be a JSON object."


def test_register_duplicate_email_ignores_case(client):
    client.post("/auth/register", json=REGISTER)
    r = client.post("/auth/register", json={**REGISTER, "email": "ALICE@example.com"})
    assert r.status_code == 409


def test_register_cannot_take_demo_email(client):
    r = client.post("/auth/register", json={**REGISTER, "email": data.DEMO_EMAIL})
    assert r.status_code == 409


def test_passwords_are_stored_hashed(client):
    client.post("/auth/register", json=REGISTER)
    stored = data.find_user_by_email("alice@example.com")
    assert "secret12" not in stored["password_hash"]
    assert "password" not in stored  # no plain-text field


# ------------------------------- login -------------------------------------

def test_demo_account_can_log_in(client):
    r = client.post("/auth/login", json={"email": data.DEMO_EMAIL, "password": data.DEMO_PASSWORD})
    assert r.status_code == 200
    assert r.get_json()["user"] == {"id": 1, "email": data.DEMO_EMAIL}


def test_login_does_not_need_confirmation(client):
    r = client.post("/auth/login", json={"email": data.DEMO_EMAIL, "password": data.DEMO_PASSWORD})
    assert r.status_code == 200


def test_login_with_registered_account(client):
    client.post("/auth/register", json=REGISTER)
    fresh = client.application.test_client()
    r = fresh.post("/auth/login", json={"email": "ALICE@example.com", "password": "secret12"})
    assert r.status_code == 200


@pytest.mark.parametrize("email, password", [
    (data.DEMO_EMAIL, "wrongpass"),
    ("nobody@example.com", "password123"),
])
def test_login_failure_is_401_with_same_message(client, email, password):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 401
    assert r.get_json()["error"] == "Wrong email or password."


def test_login_validates_input(client):
    assert client.post("/auth/login", json={"email": "bad", "password": "password123"}).status_code == 400
    assert client.post("/auth/login", json={"email": data.DEMO_EMAIL, "password": "x"}).status_code == 400
    assert client.post("/auth/login", data="nope").status_code == 400


def test_login_replaces_previous_session(client):
    client.post("/auth/register", json=REGISTER)
    client.post("/auth/login", json={"email": data.DEMO_EMAIL, "password": data.DEMO_PASSWORD})
    assert client.get("/auth/me").get_json()["user"]["email"] == data.DEMO_EMAIL


# ---------------------------- me / logout ----------------------------------

def test_me_requires_login(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_logout_ends_session(demo):
    assert demo.post("/auth/logout").status_code == 204
    assert demo.get("/auth/me").status_code == 401
    assert demo.get("/inventory").status_code == 401


def test_logout_when_not_logged_in_is_harmless(client):
    assert client.post("/auth/logout").status_code == 204


def test_sessions_are_separate_per_client(make_user, demo):
    alice = make_user()
    assert alice.get("/auth/me").get_json()["user"]["email"] == "alice@example.com"
    assert demo.get("/auth/me").get_json()["user"]["email"] == data.DEMO_EMAIL


def test_session_cookie_is_httponly_and_samesite(client):
    r = client.post("/auth/register", json=REGISTER)
    cookie = r.headers.getlist("Set-Cookie")[0]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_tampered_cookie_is_rejected(client):
    client.post("/auth/register", json=REGISTER)
    client.set_cookie("session", "tampered.value.here")
    assert client.get("/auth/me").status_code == 401
