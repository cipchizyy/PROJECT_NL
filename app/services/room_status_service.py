from datetime import datetime

from app.models.reservation import Reservation


def build_room_status_map(rooms, now=None):
    """
    Menghitung status banyak room menggunakan satu query reservasi.
    """
    now = now or datetime.utcnow()
    room_ids = [room.id for room in rooms]

    if not room_ids:
        return {}

    active_reservations = (
        Reservation.query.with_entities(
            Reservation.room_id,
            Reservation.end_time,
        )
        .filter(
            Reservation.room_id.in_(room_ids),
            Reservation.status == "confirmed",
            Reservation.start_time <= now,
            Reservation.end_time >= now,
        )
        .order_by(Reservation.end_time.asc())
        .all()
    )

    active_by_room = {}

    for reservation in active_reservations:
        # Ambil reservasi yang paling cepat selesai bila datanya overlap.
        active_by_room.setdefault(
            reservation.room_id,
            reservation,
        )

    statuses = {}

    for room in rooms:
        if room.status in ("maintenance", "inactive"):
            statuses[room.id] = {
                "state": room.status,
                "minutes_left": None,
            }
            continue

        active = active_by_room.get(room.id)

        if active:
            minutes_left = max(
                0,
                int((active.end_time - now).total_seconds() // 60),
            )

            statuses[room.id] = {
                "state": "busy",
                "minutes_left": minutes_left,
            }
        else:
            statuses[room.id] = {
                "state": "available",
                "minutes_left": None,
            }

    return statuses
