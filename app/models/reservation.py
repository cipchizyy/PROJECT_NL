import uuid
from datetime import datetime
from app.extensions import db


def generate_uuid():
    return str(uuid.uuid4())


class Reservation(db.Model):
    """
    Reservasi room. Bisa dibuat oleh Customer (online, "Make Room Reservation")
    atau oleh Admin (offline, "Create Offline Reservation").
    Update & Delete Reservation adalah <<extend>> dari Manage Room (khusus Admin).
    """
    __tablename__ = "reservations"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)

    room_id = db.Column(db.String(36), db.ForeignKey("rooms.id"), nullable=False)
    customer_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    # nullable=True karena reservasi offline yang dibuat admin bisa jadi
    # untuk pelanggan walk-in yang belum punya akun

    # Untuk reservasi offline (jika customer_id kosong)
    guest_name = db.Column(db.String(150), nullable=True)
    guest_phone = db.Column(db.String(20), nullable=True)

    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration_hours = db.Column(db.Numeric(5, 2), nullable=False)

    total_price = db.Column(db.Numeric(10, 2), nullable=False)

    status = db.Column(
        db.Enum("pending", "confirmed", "cancelled", "completed", name="reservation_status"),
        default="pending",
        nullable=False,
    )

    source = db.Column(
        db.Enum("online", "offline", name="reservation_source"),
        default="online",
        nullable=False,
    )

    created_by_admin_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    # diisi kalau reservasi dibuat lewat "Create Offline Reservation" oleh admin

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relasi
    room = db.relationship("Room", back_populates="reservations")
    customer = db.relationship("User", back_populates="reservations", foreign_keys=[customer_id])
    payment = db.relationship("Payment", back_populates="reservation", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "room_id": self.room_id,
            "customer_id": self.customer_id,
            "guest_name": self.guest_name,
            "guest_phone": self.guest_phone,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_hours": float(self.duration_hours),
            "total_price": float(self.total_price),
            "status": self.status,
            "source": self.source,
        }

    def __repr__(self):
        return f"<Reservation {self.id} room={self.room_id}>"
