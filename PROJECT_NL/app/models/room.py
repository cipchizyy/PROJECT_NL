import uuid
from datetime import datetime
from app.extensions import db


def generate_uuid():
    return str(uuid.uuid4())


class Room(db.Model):
    """
    Room/unit PlayStation yang bisa disewa.
    Terkait use case: Choose Available Room, View Room Schedule, Manage Room (Admin).
    """
    __tablename__ = "rooms"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)              # mis: "Room A - PS5"
    console_type = db.Column(db.String(50), nullable=False)        # mis: "PS5", "PS4 Pro"
    price_per_hour = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)           # URL hasil upload Cloudinary

    status = db.Column(
        db.Enum("available", "maintenance", "inactive", name="room_status"),
        default="available",
        nullable=False,
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relasi
    reservations = db.relationship("Reservation", back_populates="room", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "console_type": self.console_type,
            "price_per_hour": float(self.price_per_hour),
            "description": self.description,
            "image_url": self.image_url,
            "status": self.status,
        }

    def __repr__(self):
        return f"<Room {self.name}>"
