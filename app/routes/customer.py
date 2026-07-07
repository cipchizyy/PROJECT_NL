from flask import Blueprint, flash, render_template, request, jsonify, redirect, url_for, abort
from flask_login import login_required, current_user
import json
import uuid
import logging
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Room, Reservation, Payment

customer_bp = Blueprint("customer", __name__, url_prefix="/customer")
log = logging.getLogger(__name__)

_sim_transactions: dict = {}


@customer_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("customer/dashboard.html", user=current_user)


@customer_bp.route("/rooms")
@login_required
def view_room_schedule():
    rooms = Room.query.filter(
        Room.status != 'inactive'
    ).order_by(Room.room_code).all()
    return render_template(
        "customer/choose_room.html",
        rooms=rooms,
        has_rooms=len(rooms) > 0,
        rooms_json=json.dumps([r.to_dict_with_games() for r in rooms])
    )

@customer_bp.route("/rooms/<room_id>")
@login_required
def room_detail(room_id):
    """
    Detail satu room dari POV Customer, menampilkan macam-macam game
    yang tersedia di room tersebut (relasi Room <-> Game).
    """
    room = Room.query.get_or_404(room_id)
    return render_template(
        "customer/room_detail.html", user=current_user, active_page="rooms", room=room
    )

@customer_bp.route("/reservations", methods=["GET"])
@login_required
def view_reservation():
    reservations = (
        Reservation.query.filter_by(customer_id=current_user.id)
        .filter(Reservation.status.in_(["confirmed", "completed"]))
        .order_by(Reservation.start_time.desc())
        .all()
    )
    return render_template("customer/reservations.html", reservations=reservations, user=current_user)


@customer_bp.route("/reservations", methods=["POST"])
@login_required
def make_reservation():
    room_id        = request.form.get("room_id")
    start_time_str = request.form.get("start_time")

    if not room_id or not start_time_str:
        return jsonify(success=False, message="room_id dan start_time wajib diisi."), 400

    try:
        duration_hours = float(request.form.get("duration_hours", 1))
    except (TypeError, ValueError):
        return jsonify(success=False, message="duration_hours tidak valid."), 400

    if duration_hours <= 0 or duration_hours > 24:
        return jsonify(success=False, message="duration_hours harus antara 0 dan 24 jam."), 400

    try:
        start_time = datetime.fromisoformat(start_time_str)
    except ValueError:
        try:
            start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            return jsonify(success=False, message="Format start_time tidak valid."), 400

    end_time = start_time + timedelta(hours=duration_hours)
    room     = Room.query.get_or_404(room_id)

    conflict = Reservation.query.filter(
        Reservation.room_id == room.id,
        Reservation.status.in_(["pending", "confirmed"]),
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    ).first()
    if conflict:
        return jsonify(success=False, message="Slot waktu ini sudah dibooking, silakan pilih waktu lain."), 409

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
        redirect_url=url_for("customer.payment_page", reservation_id=reservation.id)
    )


@customer_bp.route("/rooms/<string:room_id>/booked-slots", methods=["GET"])
@login_required
def get_booked_slots(room_id):
    date_str = request.args.get("date")
    if not date_str:
        return jsonify(slots=[])

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify(slots=[])

    reservations = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.status.in_(["pending", "confirmed"]),
        db.func.date(Reservation.start_time) == target_date,
    ).all()

    slots = [
        {
            "start_time": r.start_time.isoformat(),
            "end_time":   r.end_time.isoformat(),
        }
        for r in reservations
    ]

    return jsonify(slots=slots)

@customer_bp.route("/reservations/<string:reservation_id>/cancel", methods=["POST"])
@login_required
def cancel_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.customer_id != current_user.id:
        flash("Tidak diizinkan membatalkan reservasi ini.", "danger")
        return redirect(url_for("customer.view_reservation"))

    if reservation.status != "pending":
        flash("Hanya reservasi pending yang bisa dibatalkan.", "warning")
        return redirect(url_for("customer.view_reservation"))

    reservation.status = "cancelled"
    db.session.commit()
    flash("Reservasi berhasil dibatalkan.", "success")
    return redirect(url_for("customer.view_reservation"))


@customer_bp.route("/payment/<string:reservation_id>", methods=["GET"])
@login_required
def payment_page(reservation_id: str):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.customer_id != current_user.id:
        abort(403)

    if reservation.status == "confirmed":
        return redirect(url_for("customer.invoice", reservation_id=reservation.id))

    room = Room.query.get_or_404(reservation.room_id)

    return render_template(
        "customer/payment.html",
        reservation=reservation,
        room=room,
        price_per_hour=float(room.price_per_hour),
        selected_method="cashless",
        timedelta=timedelta,
        user=current_user,
    )


@customer_bp.route("/payment/qris/generate", methods=["POST"])
@login_required
def generate_qris():
    data           = request.get_json(force=True)
    reservation_id = data.get("reservation_id")
    amount         = int(data.get("amount", 0))

    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.customer_id != current_user.id:
        return jsonify(success=False, message="Akses ditolak."), 403

    if reservation.status != "pending":
        return jsonify(success=False, message="Reservasi ini tidak dapat dibayar (status bukan pending)."), 400

    if amount != int(round(float(reservation.total_price))):
        return jsonify(success=False, message="Nominal pembayaran tidak sesuai."), 400

    ref_id     = f"SIM-{uuid.uuid4().hex[:12].upper()}"
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    _sim_transactions[ref_id] = {
        "status":         "pending",
        "expires_at":     expires_at,
        "amount":         amount,
        "reservation_id": reservation_id,
    }

    qr_payload   = f"NEXTLEVEL|{ref_id}|IDR{amount}"
    qr_image_url = (
        f"https://api.qrserver.com/v1/create-qr-code/"
        f"?size=200x200&data={qr_payload}&bgcolor=ffffff&color=000000"
    )

    return jsonify(
        success=True,
        reference_id=ref_id,
        qr_image_url=qr_image_url,
        expires_at=expires_at.isoformat() + "Z",
        sim_confirm_url=url_for("customer.sim_confirm_qris", reference_id=ref_id),
    )


@customer_bp.route("/payment/qris/status/<reference_id>", methods=["GET"])
@login_required
def check_qris_status(reference_id: str):
    trx = _sim_transactions.get(reference_id)
    if not trx:
        return jsonify(status="not_found"), 404

    if datetime.utcnow() > trx["expires_at"] and trx["status"] == "pending":
        trx["status"] = "expire"

    return jsonify(status=trx["status"])


@customer_bp.route("/payment/qris/sim-confirm/<reference_id>", methods=["POST"])
@login_required
def sim_confirm_qris(reference_id: str):
    trx = _sim_transactions.get(reference_id)
    if not trx:
        return jsonify(success=False, message="Transaksi tidak ditemukan."), 404

    if trx["status"] == "expire":
        return jsonify(success=False, message="Transaksi sudah kadaluarsa."), 400

    trx["status"] = "settlement"
    return jsonify(success=True, status="settlement")


@customer_bp.route("/payment/confirm", methods=["POST"])
@login_required
def confirm_payment():
    data           = request.get_json(force=True)
    reservation_id = data.get("reservation_id")
    reference_id   = data.get("reference_id")
    method         = data.get("method", "cashless")

    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.customer_id != current_user.id:
        return jsonify(success=False, message="Akses ditolak."), 403

    trx = _sim_transactions.get(reference_id)
    if not trx or trx["status"] != "settlement":
        return jsonify(success=False, message="Pembayaran belum terkonfirmasi."), 400

    if trx["reservation_id"] != reservation_id:
        return jsonify(success=False, message="Referensi pembayaran tidak sesuai dengan reservasi ini."), 400

    payment = Payment.query.filter_by(reservation_id=reservation.id).first()
    if not payment:
        payment = Payment(reservation_id=reservation.id)

    payment.method             = method
    payment.cashless_reference = reference_id
    payment.cashless_provider  = "QRIS"
    payment.status             = "paid"
    payment.amount             = reservation.total_price
    payment.paid_at            = datetime.utcnow()

    reservation.status = "confirmed"

    db.session.add(payment)
    db.session.commit()

    _sim_transactions.pop(reference_id, None)

    return jsonify(
        success=True,
        redirect_url=url_for("customer.invoice", reservation_id=reservation.id)
    )


@customer_bp.route("/invoice/<string:reservation_id>", methods=["GET"])
@login_required
def invoice(reservation_id: str):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.customer_id != current_user.id:
        abort(403)

    room    = Room.query.get_or_404(reservation.room_id)
    payment = Payment.query.filter_by(reservation_id=reservation.id).first()

    return render_template(
        "customer/invoice.html",
        reservation=reservation,
        room=room,
        payment=payment,
        user=current_user,
    )