from app.extensions import db

# Tabel pivot many-to-many antara Room dan Game.
# Satu room bisa punya banyak game, satu game bisa dipasang di banyak room.
# Ditaruh di file terpisah supaya room.py dan game.py bisa sama-sama
# mengimpornya tanpa circular import.
room_games = db.Table(
    "room_games",
    db.Column(
        "room_id",
        db.String(36),
        db.ForeignKey("rooms.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "game_id",
        db.String(36),
        db.ForeignKey("games.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)