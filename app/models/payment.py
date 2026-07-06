import uuid
from datetime import datetime
from app.extensions import db


def generate_uuid():
    return str(uuid.uuid4())


class Payment(db.Model):
    __tablename__ = "payments"

    id             = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    reservation_id = db.Column(db.String(36), db.ForeignKey("reservations.id"), nullable=False, unique=True)

    amount = db.Column(db.Numeric(10, 2), nullable=False)

    method = db.Column(
        db.Enum("cash", "cashless", name="payment_method"),
        nullable=False,
    )

    cashless_provider  = db.Column(db.String(50),  nullable=True)
    cashless_reference = db.Column(db.String(150), nullable=True)  # ← ini yang dipakai, bukan "reference"

    status = db.Column(
        db.Enum("pending", "paid", "failed", "refunded", name="payment_status"),
        default="pending",
        nullable=False,
    )

    paid_at    = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reservation = db.relationship("Reservation", back_populates="payment")
    def to_dict(self):
        return {
            "id":                  self.id,
            "reservation_id":      self.reservation_id,
            "amount":              float(self.amount),
            "method":              self.method,
            "cashless_provider":   self.cashless_provider,
            "cashless_reference":  self.cashless_reference,
            "status":              self.status,
            "paid_at":             self.paid_at.isoformat() if self.paid_at else None,
        }