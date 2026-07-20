from datetime import datetime, timedelta
import uuid

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.models import Payment, Reservation, Room
from app.models.associations import room_games
from app.services.room_status_service import build_room_status_map
from app.utils.cloudinary_client import cloudinary_thumbnail_url

customer_bp = Blueprint("customer", __name__, url_prefix="/customer")

# Hanya cocok untuk simulasi lokal.
# Pada serverless seperti Vercel, isi dictionary dapat hilang antar-request.
# Untuk production, simpan transaksi QRIS di database atau shared cache.
_sim_transactions: dict[str, dict] = {}


@customer_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "customer/dashboard.html",
        user=current_user,
    )


@customer_bp.route("/rooms")
@login_required
def view_room_schedule():
    rooms = Room.query.filter(Room.status != "inactive").order_by(Room.room_code).all()

    room_statuses = build_room_status_map(rooms)

    room_ids = [room.id for room in rooms]

    game_counts = {}

    if room_ids:
        count_rows = (
            db.session.query(
                room_games.c.room_id,
                func.count(room_games.c.game_id),
            )
            .filter(room_games.c.room_id.in_(room_ids))
            .group_by(room_games.c.room_id)
            .all()
        )

        game_counts = {room_id: int(total) for room_id, total in count_rows}

    rooms_data = [
        {
            "id": room.id,
            "room_code": room.room_code,
            "environment_label": room.environment_label,
            "price_per_hour": float(room.price_per_hour),
        }
        for room in rooms
    ]

    return render_template(
        "customer/choose_room.html",
        rooms=rooms,
        room_statuses=room_statuses,
        game_counts=game_counts,
        has_rooms=bool(rooms),
        rooms_data=rooms_data,
        user=current_user,
    )


@customer_bp.route("/rooms/<string:room_id>")
@login_required
def room_detail(room_id):
    """
    URL detail lama diarahkan kembali ke halaman choose room.
    """
    return redirect(
        url_for(
            "customer.view_room_schedule",
            selected_room=room_id,
        )
    )


@customer_bp.route(
    "/rooms/<string:room_id>/games",
    methods=["GET"],
)
@login_required
def get_room_games(room_id):
    """
    Mengambil daftar game hanya ketika modal Details dibuka.
    """
    room = (
        Room.query.options(selectinload(Room.games))
        .filter_by(id=room_id)
        .first_or_404()
    )

    games = [
        {
            "id": game.id,
            "name": game.name,
            "category": game.category,
            "image_url": cloudinary_thumbnail_url(
                game.image_url,
                240,
                135,
            ),
        }
        for game in room.games
    ]

    return jsonify(
        room_id=room.id,
        games=games,
    )


@customer_bp.route("/reservations", methods=["GET"])
@login_required
def view_reservation():
    """
    Riwayat reservasi customer dengan pagination.

    Relasi Room dimuat secara bulk agar template tidak menjalankan
    query tambahan untuk setiap reservasi.
    """
    page = request.args.get("page", 1, type=int)

    pagination = (
        Reservation.query
        .options(joinedload(Reservation.room))
        .filter_by(customer_id=current_user.id)
        .filter(
            Reservation.status.in_(
            ["pending", "confirmed", "completed"]
            )
    )
    .order_by(Reservation.start_time.desc())
    .paginate(
        page=page,
        per_page=10,
        error_out=False,
    )
)
    return render_template(
        "customer/reservations.html",
        reservations=pagination.items,
        pagination=pagination,
        user=current_user,
    )


@customer_bp.route("/reservations", methods=["POST"])
@login_required
def make_reservation():
    """
    Membuat reservasi online.

    Pengecekan bentrok memakai kondisi overlap dan index:
    room_id + status + start_time/end_time.
    """
    room_id = request.form.get("room_id")
    start_time_str = request.form.get("start_time")

    if not room_id or not start_time_str:
        return (
            jsonify(
                success=False,
                message="room_id dan start_time wajib diisi.",
            ),
            400,
        )

    try:
        duration_hours = float(request.form.get("duration_hours", 1))
    except (TypeError, ValueError):
        return (
            jsonify(
                success=False,
                message="duration_hours tidak valid.",
            ),
            400,
        )

    if duration_hours <= 0 or duration_hours > 24:
        return (
            jsonify(
                success=False,
                message="duration_hours harus antara 0 dan 24 jam.",
            ),
            400,
        )

    try:
        start_time = datetime.fromisoformat(start_time_str)
    except ValueError:
        try:
            start_time = datetime.strptime(
                start_time_str,
                "%Y-%m-%dT%H:%M",
            )
        except ValueError:
            return (
                jsonify(
                    success=False,
                    message="Format start_time tidak valid.",
                ),
                400,
            )

    end_time = start_time + timedelta(hours=duration_hours)

    room = Room.query.filter_by(id=room_id).first_or_404()

    if room.status != "available":
        return (
            jsonify(
                success=False,
                message="Room sedang tidak tersedia.",
            ),
            409,
        )

    conflict = Reservation.query.filter(
        Reservation.room_id == room.id,
        Reservation.status.in_(["pending", "confirmed"]),
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    ).first()

    if conflict:
        return (
            jsonify(
                success=False,
                message=(
                    "Slot waktu ini sudah dibooking, " "silakan pilih waktu lain."
                ),
            ),
            409,
        )

    total_price = float(room.price_per_hour) * duration_hours

    reservation = Reservation(
        room_id=room.id,
        customer_id=current_user.id,
        start_time=start_time,
        end_time=end_time,
        duration_hours=duration_hours,
        total_price=total_price,
        source="online",
        status="pending",
    )

    db.session.add(reservation)
    db.session.commit()

    return jsonify(
        success=True,
        redirect_url=url_for(
            "customer.payment_page",
            reservation_id=reservation.id,
        ),
    )


@customer_bp.route(
    "/rooms/<string:room_id>/booked-slots",
    methods=["GET"],
)
@login_required
def get_booked_slots(room_id):
    """
    Mengambil slot terisi pada satu tanggal.

    Filter rentang datetime dipakai agar index start_time
    tetap bisa digunakan database.
    """
    date_str = request.args.get("date", "").strip()
    if not date_str:
        return jsonify(slots=[])

    try:
        target_date = datetime.strptime(
            date_str,
            "%Y-%m-%d",
        ).date()
    except ValueError:
        return jsonify(slots=[])

    day_start = datetime.combine(
        target_date,
        datetime.min.time(),
    )
    day_end = day_start + timedelta(days=1)

    reservations = (
        Reservation.query.filter(
            Reservation.room_id == room_id,
            Reservation.status.in_(["pending", "confirmed"]),
            Reservation.start_time >= day_start,
            Reservation.start_time < day_end,
        )
        .order_by(Reservation.start_time.asc())
        .all()
    )

    return jsonify(
        slots=[
            {
                "start_time": reservation.start_time.isoformat(),
                "end_time": reservation.end_time.isoformat(),
            }
            for reservation in reservations
        ]
    )


@customer_bp.route(
    "/reservations/<string:reservation_id>/cancel",
    methods=["POST"],
)
@login_required
def cancel_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.customer_id != current_user.id:
        flash(
            "Tidak diizinkan membatalkan reservasi ini.",
            "danger",
        )
        return redirect(url_for("customer.view_reservation"))

    if reservation.status != "pending":
        flash(
            "Hanya reservasi pending yang bisa dibatalkan.",
            "warning",
        )
        return redirect(url_for("customer.view_reservation"))

    reservation.status = "cancelled"
    db.session.commit()

    flash(
        "Reservasi berhasil dibatalkan.",
        "success",
    )
    return redirect(url_for("customer.view_reservation"))


@customer_bp.route(
    "/payment/<string:reservation_id>",
    methods=["GET"],
)
@login_required
def payment_page(reservation_id: str):
    """
    Reservation dan Room dimuat dalam satu query.
    """
    reservation = (
        Reservation.query.options(joinedload(Reservation.room))
        .filter_by(id=reservation_id)
        .first_or_404()
    )

    if reservation.customer_id != current_user.id:
        abort(403)

    if reservation.status == "confirmed":
        return redirect(
            url_for(
                "customer.invoice",
                reservation_id=reservation.id,
            )
        )

    room = reservation.room
    if room is None:
        abort(404)

    return render_template(
        "customer/payment.html",
        reservation=reservation,
        room=room,
        price_per_hour=float(room.price_per_hour),
        selected_method="cashless",
        timedelta=timedelta,
        user=current_user,
    )


@customer_bp.route(
    "/payment/qris/generate",
    methods=["POST"],
)
@login_required
def generate_qris():
    data = request.get_json(silent=True) or {}
    reservation_id = data.get("reservation_id")

    try:
        amount = int(data.get("amount", 0))
    except (TypeError, ValueError):
        return (
            jsonify(
                success=False,
                message="Nominal pembayaran tidak valid.",
            ),
            400,
        )

    if not reservation_id:
        return (
            jsonify(
                success=False,
                message="Reservation ID wajib diisi.",
            ),
            400,
        )

    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.customer_id != current_user.id:
        return (
            jsonify(
                success=False,
                message="Akses ditolak.",
            ),
            403,
        )

    if reservation.status != "pending":
        return (
            jsonify(
                success=False,
                message=(
                    "Reservasi ini tidak dapat dibayar " "(status bukan pending)."
                ),
            ),
            400,
        )

    expected_amount = int(round(float(reservation.total_price)))

    if amount != expected_amount:
        return (
            jsonify(
                success=False,
                message="Nominal pembayaran tidak sesuai.",
            ),
            400,
        )

    reference_id = f"SIM-{uuid.uuid4().hex[:12].upper()}"
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    _sim_transactions[reference_id] = {
        "status": "pending",
        "expires_at": expires_at,
        "amount": amount,
        "reservation_id": reservation_id,
        "customer_id": current_user.id,
    }

    qr_payload = f"NEXTLEVEL|{reference_id}|IDR{amount}"
    qr_image_url = (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size=200x200&data={qr_payload}"
        "&bgcolor=ffffff&color=000000"
    )

    return jsonify(
        success=True,
        reference_id=reference_id,
        qr_image_url=qr_image_url,
        expires_at=expires_at.isoformat() + "Z",
        sim_confirm_url=url_for(
            "customer.sim_confirm_qris",
            reference_id=reference_id,
        ),
    )


@customer_bp.route(
    "/payment/qris/status/<string:reference_id>",
    methods=["GET"],
)
@login_required
def check_qris_status(reference_id: str):
    transaction = _sim_transactions.get(reference_id)

    if not transaction:
        return jsonify(status="not_found"), 404

    if transaction.get("customer_id") != current_user.id:
        return jsonify(status="not_found"), 404

    if (
        datetime.utcnow() > transaction["expires_at"]
        and transaction["status"] == "pending"
    ):
        transaction["status"] = "expire"

    return jsonify(status=transaction["status"])


@customer_bp.route(
    "/payment/qris/sim-confirm/<string:reference_id>",
    methods=["POST"],
)
@login_required
def sim_confirm_qris(reference_id: str):
    transaction = _sim_transactions.get(reference_id)

    if not transaction:
        return (
            jsonify(
                success=False,
                message="Transaksi tidak ditemukan.",
            ),
            404,
        )

    if transaction.get("customer_id") != current_user.id:
        return (
            jsonify(
                success=False,
                message="Akses ditolak.",
            ),
            403,
        )

    if datetime.utcnow() > transaction["expires_at"]:
        transaction["status"] = "expire"

    if transaction["status"] == "expire":
        return (
            jsonify(
                success=False,
                message="Transaksi sudah kadaluarsa.",
            ),
            400,
        )

    transaction["status"] = "settlement"

    return jsonify(
        success=True,
        status="settlement",
    )


@customer_bp.route(
    "/payment/confirm",
    methods=["POST"],
)
@login_required
def confirm_payment():
    data = request.get_json(silent=True) or {}
    reservation_id = data.get("reservation_id")
    reference_id = data.get("reference_id")
    method = data.get("method", "cashless")

    if not reservation_id:
        return (
            jsonify(
                success=False,
                message="Reservation ID wajib diisi.",
            ),
            400,
        )

    if method not in {"cash", "cashless"}:
        return (
            jsonify(
                success=False,
                message="Metode pembayaran tidak valid.",
            ),
            400,
        )

    # Reservation dan Payment dimuat dalam satu query.
    reservation = (
        Reservation.query.options(joinedload(Reservation.payment))
        .filter_by(id=reservation_id)
        .first_or_404()
    )

    if reservation.customer_id != current_user.id:
        return (
            jsonify(
                success=False,
                message="Akses ditolak.",
            ),
            403,
        )

    if reservation.status != "pending":
        return (
            jsonify(
                success=False,
                message=(
                    "Reservasi ini tidak dapat dibayar " "(status bukan pending)."
                ),
            ),
            400,
        )

    payment = reservation.payment

    if payment is None:
        payment = Payment(reservation_id=reservation.id)

    if method == "cash":
        payment.method = "cash"
        payment.status = "pending"
        payment.amount = reservation.total_price

        reservation.status = "confirmed"

        db.session.add(payment)
        db.session.commit()

        return jsonify(
            success=True,
            redirect_url=url_for(
                "customer.invoice",
                reservation_id=reservation.id,
            ),
        )

    transaction = _sim_transactions.get(reference_id)

    if not transaction:
        return (
            jsonify(
                success=False,
                message="Transaksi tidak ditemukan.",
            ),
            400,
        )

    if transaction.get("customer_id") != current_user.id:
        return (
            jsonify(
                success=False,
                message="Akses ditolak.",
            ),
            403,
        )

    if datetime.utcnow() > transaction["expires_at"]:
        transaction["status"] = "expire"

    if transaction["status"] != "settlement":
        return (
            jsonify(
                success=False,
                message="Pembayaran belum terkonfirmasi.",
            ),
            400,
        )

    if transaction["reservation_id"] != reservation_id:
        return (
            jsonify(
                success=False,
                message=("Referensi pembayaran tidak sesuai " "dengan reservasi ini."),
            ),
            400,
        )

    expected_amount = int(round(float(reservation.total_price)))

    if int(transaction["amount"]) != expected_amount:
        return (
            jsonify(
                success=False,
                message="Nominal transaksi tidak sesuai.",
            ),
            400,
        )

    payment.method = "cashless"
    payment.cashless_reference = reference_id
    payment.cashless_provider = "QRIS"
    payment.status = "paid"
    payment.amount = reservation.total_price
    payment.paid_at = datetime.utcnow()

    reservation.status = "confirmed"

    db.session.add(payment)
    db.session.commit()

    _sim_transactions.pop(reference_id, None)

    return jsonify(
        success=True,
        redirect_url=url_for(
            "customer.invoice",
            reservation_id=reservation.id,
        ),
    )


@customer_bp.route(
    "/invoice/<string:reservation_id>",
    methods=["GET"],
)
@login_required
def invoice(reservation_id: str):
    """
    Reservation, Room, dan Payment dimuat dalam satu query.
    """
    reservation = (
        Reservation.query.options(
            joinedload(Reservation.room),
            joinedload(Reservation.payment),
        )
        .filter_by(id=reservation_id)
        .first_or_404()
    )

    if reservation.customer_id != current_user.id:
        abort(403)

    room = reservation.room
    payment = reservation.payment

    if room is None:
        abort(404)

    return render_template(
        "customer/invoice.html",
        reservation=reservation,
        room=room,
        payment=payment,
        user=current_user,
    )
