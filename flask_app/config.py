import os
import secrets

class Config:
    #   print(secrets.token_hex(16))
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:Abhyodhya%402@localhost/flask_db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
    PRODUCT_UPLOAD_SUBDIR = "uploads/products"
    OFFER_BANNER_UPLOAD_SUBDIR = "uploads/banners"
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
