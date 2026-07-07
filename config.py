import os
from dotenv import load_dotenv

# Load .env dari root project
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Konfigurasi dasar yang dipakai semua environment."""

    # --- Flask Core ---
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-jangan-dipakai-di-production")

    # --- TiDB Cloud Serverless (via PyMySQL) ---
    TIDB_HOST = os.getenv("TIDB_HOST")
    TIDB_PORT = os.getenv("TIDB_PORT", "4000")
    TIDB_USER = os.getenv("TIDB_USER")
    TIDB_PASSWORD = os.getenv("TIDB_PASSWORD")
    TIDB_DATABASE = os.getenv("TIDB_DATABASE")
    TIDB_SSL_CA = os.getenv("TIDB_SSL_CA")

    # SQLAlchemy connection string ke TiDB (kompatibel protokol MySQL)
    SQLALCHEMY_DATABASE_URI = (
    f"mysql+pymysql://{TIDB_USER}:{TIDB_PASSWORD}@{TIDB_HOST}:{TIDB_PORT}/{TIDB_DATABASE}"
    f"?ssl_verify_cert=true&ssl_verify_identity=true&ssl_ca={TIDB_SSL_CA}"
    if TIDB_SSL_CA else
    f"mysql+pymysql://{TIDB_USER}:{TIDB_PASSWORD}@{TIDB_HOST}:{TIDB_PORT}/{TIDB_DATABASE}"
    f"?ssl_verify_cert=false"
)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,   # TiDB Cloud suka memutus idle connection, refresh sebelum itu
        "pool_pre_ping": True,
    }

    # --- Resend (Email) ---
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL")
    RESEND_FROM_NAME = os.getenv("RESEND_FROM_NAME", "Next Level Rent")

    # --- Cloudinary (Upload Gambar) ---
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

    # --- App Settings ---
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")
    ADMIN_CONTACT_EMAIL = os.getenv("ADMIN_CONTACT_EMAIL")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    # Untuk testing, biar tidak nyentuh TiDB Cloud asli, fallback ke sqlite in-memory
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
