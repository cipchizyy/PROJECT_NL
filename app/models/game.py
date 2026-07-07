import uuid
from datetime import datetime
from app.extensions import db
from app.models.associations import room_games


def generate_uuid():
    return str(uuid.uuid4())


class Game(db.Model):
    """
    Game yang bisa dimainkan di sebuah room (mis: PS5 - God of War Ragnarok).
    Terkait use case: Manage Game (Admin) -> Input Game -> Assign Game to Room.
    Dari POV Customer, game-game ini muncul di halaman detail room.
    """
    __tablename__ = "games"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(150), nullable=False)          # mis: "God of War Ragnarok"
    category = db.Column(db.String(50), nullable=True)         # mis: "PS5", "PS4", "Switch"
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)       # URL hasil upload Cloudinary

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relasi many-to-many ke Room lewat tabel pivot room_games
    rooms = db.relationship("Room", secondary=room_games, back_populates="games")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "image_url": self.image_url,
            "room_count": len(self.rooms),
        }

    def __repr__(self):
        return f"<Game {self.name}>"