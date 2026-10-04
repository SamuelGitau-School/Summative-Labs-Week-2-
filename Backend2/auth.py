import re

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

import data

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

EMAIL_RE = re.compile(r"^\S+@\S+\.\S+$")


def current_user():
    """The logged-in user (from the session cookie), or None."""
    user_id = session.get("user_id")
    return data.find_user(user_id) if user_id else None


def require_login():
    """before_request hook: refuse the request unless someone is logged in."""
    if current_user() is None:
        return jsonify(error="Please sign in."), 401


def public(user):
    return {"id": user["id"], "email": user["email"]}


def read_credentials(confirm=False):
    """Returns (email, password, error) from the request body.

    confirm=True (registration) also requires `confirm_password` to match.
    """
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return None, None, "Request body must be a JSON object."
    email, password = body.get("email"), body.get("password")
    if not isinstance(email, str) or not EMAIL_RE.match(email.strip()):
        return None, None, "Enter a valid email address."
    if not isinstance(password, str) or len(password) < 6:
        return None, None, "Password must be at least 6 characters."
    if confirm:
        confirm_password = body.get("confirm_password")
        if not isinstance(confirm_password, str) or not confirm_password:
            return None, None, "Please confirm your password."
        if confirm_password != password:
            return None, None, "Passwords do not match."
    return email.strip(), password, None


def start_session(user):
    session.clear()  # drop anything left over from a previous login
    session.permanent = True
    session["user_id"] = user["id"]


@auth_bp.post("/register")
def register():
    email, password, error = read_credentials(confirm=True)
    if error:
        return jsonify(error=error), 400
    if data.find_user_by_email(email):
        return jsonify(error="That email is already registered."), 409
    user = data.add_user(email, password)
    start_session(user)
    return jsonify(user=public(user)), 201


@auth_bp.post("/login")
def login():
    email, password, error = read_credentials()
    if error:
        return jsonify(error=error), 400
    user = data.find_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Wrong email or password."), 401
    start_session(user)
    return jsonify(user=public(user))


@auth_bp.post("/logout")
def logout():
    session.clear()
    return "", 204


@auth_bp.get("/me")
def me():
    """Who is logged in? The frontend calls this on page load."""
    user = current_user()
    if not user:
        return jsonify(error="Not signed in."), 401
    return jsonify(user=public(user))
