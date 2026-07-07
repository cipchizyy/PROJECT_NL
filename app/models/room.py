import uuid
from datetime import datetime
from app.extensions import db
from app.models.associations import room_games


def generate_uuid():
    return str(uuid.uuid4())


class Room(db.Model):
    """
    Room/unit PlayStation yang bisa disewa.
    Terkait use case: Choose Available Room, View Room Schedule, Manage Room (Admin).

    Sesuai mockup "CUST-Choose Room": setiap room punya kode (R-01), kategori
    environment (Regular/Regular Pro/VIP), dan daftar fasilitas singkat yang
    ditampilkan sebagai bullet list di card (jumlah game, tipe ruangan, seating).
    """
    __tablename__ = "rooms"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)

    room_code = db.Column(db.String(20), unique=True, nullable=False)   # mis: "R-01"
    name = db.Column(db.String(100), nullable=False)                     # mis: "Room A"
    console_type = db.Column(db.String(50), nullable=False)              # mis: "PS5", "PS4 Pro"

    environment = db.Column(
        db.Enum("regular", "regular_pro", "vip", name="room_environment"),
        default="regular",
        nullable=False,
    )

    price_per_hour = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)                 # URL hasil upload Cloudinary

    # --- Fasilitas singkat, ditampilkan sebagai bullet list di card ---
    # Catatan: game_count TIDAK disimpan sebagai kolom lagi, tapi dihitung
    # otomatis dari relasi `games` (lihat property di bawah), supaya tidak ada
    # dua sumber data yang bisa nggak sinkron saat admin assign/un-assign game.
    room_type = db.Column(
        db.Enum("smoking", "non_smoking", name="room_smoking_type"),
        default="non_smoking",
        nullable=False,
    )
    seating_type = db.Column(db.String(100), nullable=True)              # mis: "Cozy Beanbag Seating"

    # Status dasar di-set manual oleh Admin (Manage Room). Status "sibuk karena
    # sedang dipakai sesi berjalan" itu DIHITUNG, bukan disimpan -- lihat
    # current_status() di bawah, supaya tidak perlu job terjadwal untuk update-update.
    status = db.Column(
        db.Enum("available", "maintenance", "inactive", name="room_status"),
        default="available",
        nullable=False,
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relasi
    reservations = db.relationship("Reservation", back_populates="room", lazy="dynamic")

    # Games yang tersedia di room ini (many-to-many lewat tabel pivot room_games).
    # Terkait use case: Manage Game (Admin) -> Assign Game to Room, dan
    # dari POV Customer muncul di halaman detail room.
    games = db.relationship("Game", secondary=room_games, back_populates="rooms")

    # --- Helper tampilan ---
    @property
    def environment_label(self) -> str:
        return {
            "regular": "Regular",
            "regular_pro": "Regular Pro",
            "vip": "VIP",
        }.get(self.environment, self.environment)

    @property
    def room_type_label(self) -> str:
        return "Smoking Room" if self.room_type == "smoking" else "Non-Smoking Room"

    @property
    def game_count(self) -> int:
        """
        Jumlah game yang terpasang di room ini, dihitung langsung dari relasi
        `games` (bukan kolom manual) supaya selalu akurat begitu admin
        assign/un-assign game lewat fitur Manage Game.
        """
        return len(self.games)

    def get_active_reservation(self, now: datetime = None):
        """
        Cari reservasi yang sedang berjalan SEKARANG (start_time <= now <= end_time),
        statusnya confirmed. Dipakai untuk menghitung status real-time (Busy/Available).
        """
        from app.models.reservation import Reservation

        now = now or datetime.utcnow()
        return (
            self.reservations
            .filter(
                Reservation.status == "confirmed",
                Reservation.start_time <= now,
                Reservation.end_time >= now,
            )
            .first()
        )

    def current_status(self, now: datetime = None):
        """
        Status real-time untuk ditampilkan di card, sesuai mockup:
        - "available"   -> badge hijau "Available"
        - "busy"         -> badge merah "Busy (Xm left)", X dihitung dari reservasi aktif
        - "maintenance"/"inactive" -> ikut status dasar dari Admin

        Return: dict {"state": "available"|"busy"|"maintenance"|"inactive", "minutes_left": int|None}
        """
        now = now or datetime.utcnow()

        if self.status in ("maintenance", "inactive"):
            return {"state": self.status, "minutes_left": None}

        active_reservation = self.get_active_reservation(now)
        if active_reservation:
            minutes_left = max(0, int((active_reservation.end_time - now).total_seconds() // 60))
            return {"state": "busy", "minutes_left": minutes_left}

        return {"state": "available", "minutes_left": None}

    def to_dict(self):
        live_status = self.current_status()
        return {
            "id": self.id,
            "room_code": self.room_code,
            "name": self.name,
            "console_type": self.console_type,
            "environment": self.environment,
            "environment_label": self.environment_label,
            "price_per_hour": float(self.price_per_hour),
            "description": self.description,
            "image_url": self.image_url,
            "game_count": self.game_count,
            "room_type": self.room_type,
            "room_type_label": self.room_type_label,
            "seating_type": self.seating_type,
            "status": self.status,
            "live_status": live_status,
        }

    def to_dict_with_games(self):
        """
        Sama seperti to_dict(), ditambah daftar detail game (bukan cuma jumlahnya)
        yang terpasang di room ini. Dipisah supaya to_dict() tetap ringan dan
        tidak melakukan query tambahan kalau tidak dibutuhkan.
        """
        data = self.to_dict()
        data["games"] = [g.to_dict() for g in self.games]
        return data

    def __repr__(self):
        return f"<Room {self.room_code} {self.name}>"