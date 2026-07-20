import os
from urllib.parse import quote_plus

from dotenv import load_dotenv


# Load .env dari root project.
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


def build_tidb_database_uri():
    """
    Membuat connection string TiDB yang aman.

    quote_plus() mencegah password, username, nama database, atau path CA
    rusak ketika mengandung karakter khusus seperti @, :, /, atau spasi.
    """
    host = os.getenv("TIDB_HOST")
    port = os.getenv("TIDB_PORT", "4000")
    user = os.getenv("TIDB_USER")
    password = os.getenv("TIDB_PASSWORD")
    database = os.getenv("TIDB_DATABASE")
    ssl_ca = os.getenv("TIDB_SSL_CA")

    # TestingConfig akan mengganti URI ini dengan SQLite.
    # Untuk development/production, Flask-SQLAlchemy akan memberi error
    # yang jelas jika konfigurasi database belum lengkap.
    if not all([host, port, user, password, database]):
        return None

    user_encoded = quote_plus(user)
    password_encoded = quote_plus(password)
    database_encoded = quote_plus(database)

    base_uri = (
        f"mysql+pymysql://"
        f"{user_encoded}:{password_encoded}"
        f"@{host}:{port}/{database_encoded}"
    )

    query_params = [
        "charset=utf8mb4",
    ]

    if ssl_ca:
        query_params.extend(
            [
                "ssl_verify_cert=true",
                "ssl_verify_identity=true",
                f"ssl_ca={quote_plus(ssl_ca)}",
            ]
        )
    else:
        # Hanya cocok untuk local/testing sementara.
        # Production sebaiknya selalu mengisi TIDB_SSL_CA.
        query_params.append("ssl_verify_cert=false")

    return f"{base_uri}?{'&'.join(query_params)}"


class Config:
    """Konfigurasi dasar yang dipakai semua environment."""

    # --- Flask Core ---
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "dev-secret-key-jangan-dipakai-di-production",
    )

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    # --- TiDB Cloud Serverless (via PyMySQL) ---
    TIDB_HOST = os.getenv("TIDB_HOST")
    TIDB_PORT = os.getenv("TIDB_PORT", "4000")
    TIDB_USER = os.getenv("TIDB_USER")
    TIDB_PASSWORD = os.getenv("TIDB_PASSWORD")
    TIDB_DATABASE = os.getenv("TIDB_DATABASE")
    TIDB_SSL_CA = os.getenv("TIDB_SSL_CA")

    SQLALCHEMY_DATABASE_URI = build_tidb_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mencegah koneksi idle/stale menyebabkan request menunggu sangat lama.
    SQLALCHEMY_ENGINE_OPTIONS = {
        # Cek koneksi sebelum dipakai. Jika sudah mati, SQLAlchemy
        # otomatis membuangnya dan membuka koneksi baru.
        "pool_pre_ping": True,

        # Recycle koneksi sebelum terlalu lama idle.
        "pool_recycle": 90,

        # Gunakan koneksi yang paling baru dikembalikan ke pool.
        "pool_use_lifo": True,

        # Maksimal menunggu koneksi tersedia dari pool.
        "pool_timeout": 10,

        # Timeout pada driver PyMySQL.
        "connect_args": {
            "connect_timeout": 10,
            "read_timeout": 15,
            "write_timeout": 15,
        },
    }

    # --- Resend / Email ---
    # Hapus bagian ini jika project sudah sepenuhnya memakai smtplib
    # dan tidak lagi menggunakan library Resend.
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL")
    RESEND_FROM_NAME = os.getenv(
        "RESEND_FROM_NAME",
        "Next Level Rent",
    )

    # --- Cloudinary ---
    CLOUDINARY_CLOUD_NAME = os.getenv(
        "CLOUDINARY_CLOUD_NAME"
    )
    CLOUDINARY_API_KEY = os.getenv(
        "CLOUDINARY_API_KEY"
    )
    CLOUDINARY_API_SECRET = os.getenv(
        "CLOUDINARY_API_SECRET"
    )

    # --- App Settings ---
    APP_BASE_URL = os.getenv(
        "APP_BASE_URL",
        "http://127.0.0.1:5000",
    )
    ADMIN_CONTACT_EMAIL = os.getenv(
        "ADMIN_CONTACT_EMAIL",
        "admin@example.com",
    )
    ADMIN_CONTACT_WA = os.getenv(
        "ADMIN_CONTACT_WA",
        "6281234567890",
    )


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True

    # Jangan menyentuh TiDB saat testing.
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    # Engine options PyMySQL tidak kompatibel dengan SQLite.
    SQLALCHEMY_ENGINE_OPTIONS = {}


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
