import cloudinary.uploader
from werkzeug.datastructures import FileStorage


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_room_image(file: FileStorage, room_id: str) -> str:
    """
    Upload foto room ke Cloudinary, dipakai di fitur Manage Room (Admin).
    Mengembalikan secure_url yang nanti disimpan di kolom Room.image_url.
    """
    if not file or not allowed_file(file.filename):
        raise ValueError("Format file tidak didukung. Gunakan png/jpg/jpeg/webp.")

    result = cloudinary.uploader.upload(
        file,
        folder="next-level-rent/rooms",
        public_id=f"room_{room_id}",
        overwrite=True,
        invalidate=True,
        resource_type="image",
    )
    return result.get("secure_url")


def upload_game_image(file, game_id):
    if not file or not allowed_file(file.filename):
        raise ValueError("Format file tidak didukung. Gunakan png/jpg/jpeg/webp.")
    result = cloudinary.uploader.upload(
        file,
        folder="next-level-rent/games",
        public_id=f"game_{game_id}",
        overwrite=True,
        invalidate=True,
        resource_type="image",
    )
    return result.get("secure_url")


def delete_image(public_id: str):
    cloudinary.uploader.destroy(public_id)