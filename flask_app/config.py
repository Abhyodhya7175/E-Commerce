import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:Abhyodhya%401@localhost/flask_db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False