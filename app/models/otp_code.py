import uuid
import secrets
from datetime import datetime, timedelta
from app.extensions import db


def generate_uuid():
    return str(uuid.uuid4())


def generate_otp() -> str:
    """Membuat kode OTP acak sebanyak 6 digit."""
    return f"{secrets.randbelow(1_000_000):06d}"


class OtpCode(db.Model):
    """
    Kode OTP 6 digit untuk verifikasi email saat Sign Up.
    """
    __tablename__ = "otp_codes"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(6), nullable=False)

    purpose = db.Column(
        db.Enum("email_verification", "password_reset", name="otp_purpose"),
        default="email_verification",
        nullable=False,
    )

    is_used = db.Column(db.Boolean, default=False, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relasi
    user = db.relationship("User")

    @staticmethod
    def create_for_user(
        user_id: str,
        email: str,
        purpose: str = "email_verification",
        valid_minutes: int = 10
    ):
        """
        Buat record OTP baru.
        OTP lama untuk user dan purpose yang sama akan ditandai sudah digunakan.
        """

        # Nonaktifkan OTP lama yang belum dipakai
        OtpCode.query.filter_by(
            user_id=user_id,
            purpose=purpose,
            is_used=False
        ).update({"is_used": True})

        otp = OtpCode(
            user_id=user_id,
            email=email,
            code=generate_otp(),
            purpose=purpose,
            expires_at=datetime.utcnow() + timedelta(minutes=valid_minutes),
        )

        db.session.add(otp)
        db.session.commit()

        return otp

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def is_valid(self, input_code: str) -> bool:
        return (
            not self.is_used
            and not self.is_expired
            and self.code == input_code
        )

    def __repr__(self):
        return f"<OtpCode {self.email} {self.code} used={self.is_used}>"