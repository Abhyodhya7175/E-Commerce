import os
import secrets
from dotenv import load_dotenv
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError
from urllib.parse import quote_plus
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
ROOT_ENV_PATH = os.path.join(BASE_DIR, ".env")
APP_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

# Load environment variables from both common locations.
# Root .env is preferred for repo-level setup, flask_app/.env supports legacy local setup.
load_dotenv(ROOT_ENV_PATH)
load_dotenv(APP_ENV_PATH)


def _resolve_database_uri() -> str:
    """Return a valid SQLAlchemy DB URI from env vars, or fallback to local SQLite."""
    candidates = [
        os.getenv("SQLALCHEMY_DATABASE_URI"),
        os.getenv("DATABASE_URL"),
        os.getenv("MYSQL_DATABASE_URI"),
    ]

    for candidate in candidates:
        value = (candidate or "").strip().strip('"').strip("'")
        if not value:
            continue

        # Common Heroku-style shorthand that SQLAlchemy 2 does not accept.
        if value.startswith("postgres://"):
            value = "postgresql://" + value[len("postgres://"):]

        try:
            make_url(value)
            return value
        except ArgumentError:
            continue

    # Build MySQL URL from discrete env vars so raw passwords (with @, #, :) work.
    db_user = (os.getenv("DB_USER") or os.getenv("MYSQL_USER") or "").strip()
    db_pass = os.getenv("DB_PASSWORD") or os.getenv("MYSQL_PASSWORD") or ""
    db_host = (os.getenv("DB_HOST") or os.getenv("MYSQL_HOST") or "localhost").strip()
    db_port = (os.getenv("DB_PORT") or os.getenv("MYSQL_PORT") or "3306").strip()
    db_name = (os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE") or "").strip()

    if db_user and db_name:
        encoded_pass = quote_plus(db_pass)
        mysql_uri = f"mysql+pymysql://{db_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}"
        try:
            make_url(mysql_uri)
            return mysql_uri
        except ArgumentError:
            pass

    return f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"

class Config:
    #   print(secrets.token_hex(16))
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(16)
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
    PRODUCT_UPLOAD_SUBDIR = "uploads/products"
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
    SHIPROCKET_EMAIL = os.getenv("SHIPROCKET_EMAIL")
    SHIPROCKET_PASSWORD = os.getenv("SHIPROCKET_PASSWORD")
    SHIPROCKET_PICKUP_PINCODE = os.getenv("SHIPROCKET_PICKUP_PINCODE")
    SHIPROCKET_TIMEOUT_SECONDS = float(os.getenv("SHIPROCKET_TIMEOUT_SECONDS", "8"))
    SHIPROCKET_TOKEN_TTL_SECONDS = int(os.getenv("SHIPROCKET_TOKEN_TTL_SECONDS", "86400"))
    SHIPROCKET_CACHE_TTL_SECONDS = int(os.getenv("SHIPROCKET_CACHE_TTL_SECONDS", "21600"))
    DEFAULT_PRODUCT_WEIGHT_KG = float(os.getenv("DEFAULT_PRODUCT_WEIGHT_KG", "0.5"))
    FREE_SHIPPING_MIN = float(os.getenv("FREE_SHIPPING_MIN", "0"))