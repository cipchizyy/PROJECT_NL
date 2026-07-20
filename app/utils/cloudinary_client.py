import cloudinary


def init_cloudinary(app):
    cloudinary.config(
        cloud_name=app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=app.config["CLOUDINARY_API_KEY"],
        api_secret=app.config["CLOUDINARY_API_SECRET"],
        secure=True,
    )


def cloudinary_thumbnail_url(
    url: str | None,
    width: int = 320,
    height: int = 180,
) -> str | None:
    """
    Mengubah URL gambar Cloudinary asli menjadi URL thumbnail teroptimasi.

    f_auto  : memilih format terbaik, misalnya AVIF/WebP.
    q_auto  : memilih kualitas dan kompresi otomatis.
    c_fill  : crop gambar agar sesuai ukuran card.
    dpr_auto: menyesuaikan resolusi layar.
    """
    if not url:
        return url

    marker = "/image/upload/"

    # Jangan mengubah URL gambar non-Cloudinary.
    if "res.cloudinary.com" not in url or marker not in url:
        return url

    width = max(1, int(width))
    height = max(1, int(height))

    transformation = f"f_auto,q_auto,c_fill," f"w_{width},h_{height},dpr_auto"

    return url.replace(
        marker,
        f"{marker}{transformation}/",
        1,
    )
