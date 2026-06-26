import cloudinary


def init_cloudinary(app):
    """
    Konfigurasi Cloudinary SDK pakai kredensial dari .env (sudah dibaca di config.py
    via os.getenv, lalu di-passing lewat app.config).
    """
    cloudinary.config(
        cloud_name=app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=app.config["CLOUDINARY_API_KEY"],
        api_secret=app.config["CLOUDINARY_API_SECRET"],
        secure=True,
    )
