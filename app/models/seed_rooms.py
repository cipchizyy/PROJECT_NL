"""
Script untuk mengisi data room contoh ke database.
Jalankan dengan: python seed_rooms.py

Berguna supaya halaman "Choose Available Room" langsung ada isinya
saat pertama kali dicoba, tanpa perlu input manual lewat Admin panel.
Data dibuat mirip mockup: R-01 s/d R-06, kategori Regular.
"""
from app import create_app
from app.extensions import db
from app.models import Room

app = create_app()

SAMPLE_ROOMS = [
    {
        "room_code": "R-01", "name": "Room 01", "console_type": "PS5",
        "environment": "regular", "price_per_hour": 10000,
        "room_type": "smoking", "seating_type": "Cozy Beanbag Seating", "status": "available",
    },
    {
        "room_code": "R-02", "name": "Room 02", "console_type": "PS5",
        "environment": "regular", "price_per_hour": 10000,
        "room_type": "smoking", "seating_type": "Cozy Beanbag Seating", "status": "available",
    },
    {
        "room_code": "R-03", "name": "Room 03", "console_type": "PS5",
        "environment": "regular", "price_per_hour": 10000,
        "room_type": "smoking", "seating_type": "Cozy Beanbag Seating", "status": "available",
    },
    {
        "room_code": "R-04", "name": "Room 04", "console_type": "PS5",
        "environment": "regular", "price_per_hour": 10000, 
        "room_type": "non_smoking", "seating_type": "Cozy Beanbag Seating", "status": "available",
    },
    {
        "room_code": "R-05", "name": "Room 05", "console_type": "PS5",
        "environment": "regular", "price_per_hour": 10000,
        "room_type": "non_smoking", "seating_type": "Cozy Beanbag Seating", "status": "available",
    },
    {
        "room_code": "R-06", "name": "Room 06", "console_type": "PS5",
        "environment": "regular", "price_per_hour": 10000,
        "room_type": "non_smoking", "seating_type": "Cozy Beanbag Seating", "status": "available",
    },
    # --- Contoh isi kategori Regular Pro & VIP, biar sidebar filter ada isinya ---
    {
        "room_code": "RP-01", "name": "Pro Room 01", "console_type": "PS5 Pro",
        "environment": "regular_pro", "price_per_hour": 18000,
        "room_type": "non_smoking", "seating_type": "Gaming Chair", "status": "available",
    },
    {
        "room_code": "V-01", "name": "VIP Room 01", "console_type": "PS5 Slim",
        "environment": "vip", "price_per_hour": 30000,
        "room_type": "non_smoking", "seating_type": "Private Sofa", "status": "available",
    },
]

with app.app_context():
    existing_count = Room.query.count()

    if existing_count > 0:
        print(f"Sudah ada {existing_count} room di database. Seed dibatalkan.")
        print("Hapus data room manual dulu kalau mau seed ulang.")
    else:
        for data in SAMPLE_ROOMS:
            room = Room(**data)
            db.session.add(room)

        db.session.commit()
        print(f"Berhasil menambahkan {len(SAMPLE_ROOMS)} room contoh.")
        print("Catatan: badge 'Busy (Xm left)' di card hanya muncul kalau ada")
        print("reservasi aktif (status=confirmed, start_time <= now <= end_time)")
        print("untuk room tersebut. Buat lewat Make Room Reservation untuk tes.")