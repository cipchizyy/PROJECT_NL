import uuid
from datetime import datetime
from flask_login import UserMixin
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
    reservations = db.relationship("Reservation", back_populates="customer", lazy="dynamic")

    # --- Password helpers (passcode = password biasa, di-hash via bcrypt) ---
    def set_password(self, raw_password: str):
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

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
