import uuid
from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.extensions import db, bcrypt


def generate_uuid():
    return str(uuid.uuid4())


class User(db.Model, UserMixin):
    """
    Satu tabel untuk Customer & Admin, dibedakan lewat kolom `role`.
    Sesuai mockup Sign Up: Name, Nomor Handphone, Email, Passcode (password).
    """
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone_number = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.Enum("customer", "admin", name="user_role"), default="customer", nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relasi
    reservations = db.relationship(
        "Reservation",
        back_populates="customer",
        foreign_keys="Reservation.customer_id",
        lazy="dynamic"
    )

    # --- Password helpers (passcode = password biasa, di-hash via bcrypt) ---
    def set_password(self, raw_password: str):
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    # --- Reset password token (stateless, tidak butuh kolom/tabel baru) ---
    # Token ditandatangani pakai SECRET_KEY app, berisi email, dan punya masa
    # berlaku (default 1 jam). Aman karena tidak bisa dipalsukan tanpa SECRET_KEY,
    # dan otomatis "expired" tanpa perlu disimpan/dihapus dari DB.
    RESET_TOKEN_SALT = "password-reset-salt"

    def generate_reset_token(self) -> str:
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return serializer.dumps(self.email, salt=self.RESET_TOKEN_SALT)

    @staticmethod
    def verify_reset_token(token: str, max_age: int = 3600):
        """
        Verifikasi token reset password.
        max_age dalam detik (default 3600 = 1 jam).
        Return: User object kalau valid, None kalau token invalid/expired.
        """
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            email = serializer.loads(token, salt=User.RESET_TOKEN_SALT, max_age=max_age)
        except (BadSignature, SignatureExpired):
            return None
        return User.query.filter_by(email=email).first()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone_number": self.phone_number,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"