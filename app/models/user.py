import uuid
from datetime import datetime

from flask import current_app
from flask_login import UserMixin
from itsdangerous import (
    URLSafeTimedSerializer,
    BadSignature,
    SignatureExpired,
)

from app.extensions import db, bcrypt


def generate_uuid():
    return str(uuid.uuid4())


class User(db.Model, UserMixin):
    """
    Satu tabel untuk Customer dan Admin.
    Peran pengguna dibedakan melalui kolom role.

    Data signup:
    - Name
    - Nomor handphone
    - Email
    - Passcode
    """

    __tablename__ = "users"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=generate_uuid,
    )

    name = db.Column(
        db.String(150),
        nullable=False,
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False,
        index=True,
    )

    phone_number = db.Column(
        db.String(20),
        nullable=False,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    role = db.Column(
        db.Enum(
            "customer",
            "admin",
            name="user_role",
        ),
        default="customer",
        nullable=False,
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
    )

    is_email_verified = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relasi reservasi milik customer
    reservations = db.relationship(
        "Reservation",
        back_populates="customer",
        foreign_keys="Reservation.customer_id",
        lazy="dynamic",
    )

    # =========================================================
    # PASSWORD
    # =========================================================

    def set_password(self, raw_password: str):
        """
        Mengubah passcode asli menjadi hash bcrypt.
        """

        self.password_hash = bcrypt.generate_password_hash(
            raw_password
        ).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        """
        Memeriksa kecocokan passcode dengan password hash.
        """

        return bcrypt.check_password_hash(
            self.password_hash,
            raw_password,
        )

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    # =========================================================
    # RESET PASSWORD TOKEN
    # =========================================================

    RESET_TOKEN_SALT = "password-reset-salt"

    def generate_reset_token(self) -> str:
        """
        Membuat token reset passcode.
        """

        serializer = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"]
        )

        return serializer.dumps(
            self.email,
            salt=self.RESET_TOKEN_SALT,
        )

    @staticmethod
    def verify_reset_token(
        token: str,
        max_age: int = 3600,
    ):
        """
        Memeriksa token reset passcode.

        Default masa berlaku:
        3600 detik atau 1 jam.

        Return:
        - User jika token valid
        - None jika token salah atau kedaluwarsa
        """

        serializer = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"]
        )

        try:
            email = serializer.loads(
                token,
                salt=User.RESET_TOKEN_SALT,
                max_age=max_age,
            )
        except (BadSignature, SignatureExpired):
            return None

        return User.query.filter_by(email=email).first()

    # =========================================================
    # SERIALIZATION
    # =========================================================

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone_number": self.phone_number,
            "role": self.role,
            "is_active": self.is_active,
            "is_email_verified": self.is_email_verified,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
        }

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"