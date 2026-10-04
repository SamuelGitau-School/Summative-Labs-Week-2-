import os
from datetime import timedelta

from flask import Flask, jsonify

from auth import auth_bp
from routes import inventory_bp

app = Flask(__name__)
app.url_map.strict_slashes = False  # /inventory and /inventory/ both work

# The secret signs the session cookie. Set SECRET_KEY in the environment for
# anything beyond local development.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)

app.register_blueprint(auth_bp)
app.register_blueprint(inventory_bp)


@app.errorhandler(404)
def not_found(_):
    return jsonify(error="Not found."), 404


@app.errorhandler(405)
def method_not_allowed(_):
    return jsonify(error="Method not allowed."), 405


if __name__ == "__main__":
    app.run(debug=True, port=5000)
