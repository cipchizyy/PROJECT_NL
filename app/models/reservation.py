import uuid
import random
from datetime import datetime
from app.extensions import db


def generate_uuid():
    return str(uuid.uuid4())


def generate_booking_number():
    """Generate booking ID pendek untuk ditampilkan ke customer, mis: 'NL-9942'."""
    return f"NL-{random.randint(1000, 9999)}"


class Reservation(db.Model):
    """
    Reservasi room. Bisa dibuat oleh Customer (online, "Make Room Reservation")
    atau oleh Admin (offline, "Create Offline Reservation").
    Update & Delete Reservation adalah <<extend>> dari Manage Room (khusus Admin).
    """

    __tablename__ = "reservations"

    __table_args__ = (
        db.Index(
            "ix_reservation_room_status_start",
            "room_id",
            "status",
            "start_time",
        ),
        db.Index(
            "ix_reservation_room_status_end",
            "room_id",
            "status",
            "end_time",
        ),
        db.Index(
            "ix_reservation_customer_status_start",
            "customer_id",
            "status",
            "start_time",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    booking_number = db.Column(
        db.String(20), unique=True, nullable=False, default=generate_booking_number
    )
    # Booking ID pendek (mis: "NL-9942") yang ditampilkan di tabel Reservation List admin,
    # supaya lebih mudah disebut/dicari dibanding UUID panjang.

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
        db.Enum(
            "pending", "confirmed", "cancelled", "completed", name="reservation_status"
        ),
        default="pending",
        nullable=False,
    )

    # Terpisah dari `status`: menandai customer sudah check-in fisik di lokasi.
    # Badge "Arrived" di Reservation List admin = status confirmed + is_arrived True.
    is_arrived = db.Column(db.Boolean, default=False, nullable=False)
    arrived_at = db.Column(db.DateTime, nullable=True)

    source = db.Column(
        db.Enum("online", "offline", name="reservation_source"),
        default="online",
        nullable=False,
    )

    created_by_admin_id = db.Column(
        db.String(36), db.ForeignKey("users.id"), nullable=True
    )
    # diisi kalau reservasi dibuat lewat "Create Offline Reservation" oleh admin

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relasi
    room = db.relationship("Room", back_populates="reservations")
    customer = db.relationship(
        "User", back_populates="reservations", foreign_keys=[customer_id]
    )
    created_by_admin = db.relationship("User", foreign_keys=[created_by_admin_id])
    payment = db.relationship("Payment", back_populates="reservation", uselist=False)

    @property
    def customer_display_name(self) -> str:
        """Nama yang ditampilkan di tabel: customer terdaftar atau guest walk-in."""
        if self.customer:
            return self.customer.name
        return self.guest_name or "-"

    @property
    def display_status(self) -> str:
        """Status untuk badge di Reservation List: arrived diutamakan tampil di atas confirmed biasa."""
        if self.status == "confirmed" and self.is_arrived:
            return "arrived"
        return self.status

    def to_dict(self):
        return {
            "id": self.id,
            "booking_number": self.booking_number,
            "room_id": self.room_id,
            "customer_id": self.customer_id,
            "customer_display_name": self.customer_display_name,
            "guest_name": self.guest_name,
            "guest_phone": self.guest_phone,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_hours": float(self.duration_hours),
            "total_price": float(self.total_price),
            "status": self.status,
            "is_arrived": self.is_arrived,
            "display_status": self.display_status,
            "source": self.source,
        }

    def __repr__(self):
        return f"<Reservation {self.booking_number} room={self.room_id}>"
