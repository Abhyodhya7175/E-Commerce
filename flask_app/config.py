import os
import secrets
from dotenv import load_dotenv
load_dotenv()

class Config:
    #   print(secrets.token_hex(16))
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
    PRODUCT_UPLOAD_SUBDIR = "uploads/products"
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}