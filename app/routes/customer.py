from flask import Blueprint, render_template, request, jsonify, redirect, url_for, abort
from flask_login import login_required, current_user
import json
import uuid
import logging
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Room, Reservation, Payment

customer_bp = Blueprint("customer", __name__, url_prefix="/customer")
log = logging.getLogger(__name__)

# ─── In-memory simulasi QRIS ────────────────────────────────
# { reference_id: { "status": "pending"|"settlement", "expires_at": datetime, "amount": int } }
_sim_transactions: dict = {}


# ─────────────────────────────────────────────────────────────
#  ROUTE LAMA (tidak diubah)
# ─────────────────────────────────────────────────────────────

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
        rooms_json=json.dumps([r.to_dict() for r in rooms])
    )


@customer_bp.route("/reservations", methods=["GET"])
@login_required
def view_reservation():
    reservations = (
        Reservation.query.filter_by(customer_id=current_user.id)
        .order_by(Reservation.start_time.desc())
        .all()
    )
    return render_template("customer/payment.html", reservations=reservations)


@customer_bp.route("/reservations", methods=["POST"])
@login_required
def make_reservation():
    room_id        = request.form.get("room_id")
    start_time_str = request.form.get("start_time")
    duration_hours = float(request.form.get("duration_hours", 1))

    # ✅ Parse string → datetime
    start_time = datetime.fromisoformat(start_time_str)
    # ✅ Hitung end_time secara eksplisit
    end_time   = start_time + timedelta(hours=duration_hours)

    room        = Room.query.get_or_404(room_id)
    total_price = float(room.price_per_hour) * duration_hours

    reservation = Reservation(
        room_id=room.id,
        customer_id=current_user.id,
        start_time=start_time,
        end_time=end_time,          # ✅ Tambahkan ini
        duration_hours=duration_hours,
        total_price=total_price,
        source="online",
        status="pending",
    )
    db.session.add(reservation)
    db.session.commit()

    return jsonify({"success": True, "reservation": reservation.to_dict()}), 201

@customer_bp.route("/payments", methods=["POST"])
@login_required
def create_payment():
    reservation_id = request.form.get("reservation_id")
    method         = request.form.get("method")

    reservation = Reservation.query.get_or_404(reservation_id)

    payment = Payment(
        reservation_id=reservation.id,
        amount=reservation.total_price,
        method=method,
        status="pending" if method == "cashless" else "paid",
    )
    db.session.add(payment)
    db.session.commit()

    return jsonify({"success": True, "payment": payment.to_dict()}), 201


# ─────────────────────────────────────────────────────────────
#  PAYMENT PAGE  GET /customer/payment/<reservation_id>
# ─────────────────────────────────────────────────────────────

@customer_bp.route("/payment/<int:reservation_id>", methods=["GET"])
@login_required
def payment_page(reservation_id: int):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.customer_id != current_user.id:
        abort(403)

    if reservation.status == "paid":
        return redirect(url_for("customer.dashboard"))

    room = Room.query.get_or_404(reservation.room_id)

    return render_template(
        "customer/payment.html",
        reservation=reservation,
        room=room,
        selected_method="cashless",
    )


# ─────────────────────────────────────────────────────────────
#  [SIMULASI] GENERATE QRIS
#  POST /customer/payment/qris/generate
# ─────────────────────────────────────────────────────────────

@customer_bp.route("/payment/qris/generate", methods=["POST"])
@login_required
def generate_qris():
    """
    MODE SIMULASI — tidak memanggil Midtrans.
    Membuat reference_id lokal + QR dari api.qrserver.com (gratis, no-auth).
    Body JSON : { reservation_id, amount }
    Return    : { success, reference_id, qr_image_url, expires_at, sim_confirm_url }
    """
    data           = request.get_json(force=True)
    reservation_id = data.get("reservation_id")
    amount         = int(data.get("amount", 0))

    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.customer_id != current_user.id:
        return jsonify(success=False, message="Akses ditolak."), 403

    # Buat reference id unik
    ref_id     = f"SIM-{uuid.uuid4().hex[:12].upper()}"
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    # Simpan ke memory store
    _sim_transactions[ref_id] = {
        "status":         "pending",
        "expires_at":     expires_at,
        "amount":         amount,
        "reservation_id": reservation_id,
    }

    # QR code dari layanan publik — encode teks pembayaran sebagai payload
    qr_payload = f"NEXTLEVEL|{ref_id}|IDR{amount}"
    qr_image_url = (
        f"https://api.qrserver.com/v1/create-qr-code/"
        f"?size=200x200&data={qr_payload}&bgcolor=ffffff&color=000000"
    )

    return jsonify(
        success=True,
        reference_id=ref_id,
        qr_image_url=qr_image_url,
        expires_at=expires_at.isoformat() + "Z",
        # URL tombol "Konfirmasi Bayar" khusus simulasi
        sim_confirm_url=url_for("customer.sim_confirm_qris", reference_id=ref_id),
    )


# ─────────────────────────────────────────────────────────────
#  [SIMULASI] CEK STATUS
#  GET /customer/payment/qris/status/<reference_id>
# ─────────────────────────────────────────────────────────────

@customer_bp.route("/payment/qris/status/<reference_id>", methods=["GET"])
@login_required
def check_qris_status(reference_id: str):
    trx = _sim_transactions.get(reference_id)
    if not trx:
        return jsonify(status="not_found"), 404

    # Auto-expire
    if datetime.utcnow() > trx["expires_at"] and trx["status"] == "pending":
        trx["status"] = "expire"

    return jsonify(status=trx["status"])


# ─────────────────────────────────────────────────────────────
#  [SIMULASI] TOMBOL "KONFIRMASI BAYAR"
#  POST /customer/payment/qris/sim-confirm/<reference_id>
#  — endpoint ini menggantikan scan HP nyata —
# ─────────────────────────────────────────────────────────────

@customer_bp.route("/payment/qris/sim-confirm/<reference_id>", methods=["POST"])
@login_required
def sim_confirm_qris(reference_id: str):
    """
    Tombol simulasi: ubah status transaksi → settlement
    tanpa perlu scan QR sesungguhnya.
    """
    trx = _sim_transactions.get(reference_id)
    if not trx:
        return jsonify(success=False, message="Transaksi tidak ditemukan."), 404

    if trx["status"] == "expire":
        return jsonify(success=False, message="Transaksi sudah kadaluarsa."), 400

    trx["status"] = "settlement"
    return jsonify(success=True, status="settlement")


# ─────────────────────────────────────────────────────────────
#  KONFIRMASI FINAL — simpan ke DB
#  POST /customer/payment/confirm
# ─────────────────────────────────────────────────────────────

@customer_bp.route("/payment/confirm", methods=["POST"])
@login_required
def confirm_payment():
    """
    JS memanggil ini setelah detect status = settlement.
    Server re-verify dari _sim_transactions sebelum simpan.
    Body JSON: { reservation_id, reference_id, method }
    """
    data           = request.get_json(force=True)
    reservation_id = data.get("reservation_id")
    reference_id   = data.get("reference_id")
    method         = data.get("method", "cashless")

    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.customer_id != current_user.id:
        return jsonify(success=False, message="Akses ditolak."), 403

    # Re-verify di server
    trx = _sim_transactions.get(reference_id)
    if not trx or trx["status"] != "settlement":
        return jsonify(success=False, message="Pembayaran belum terkonfirmasi."), 400

    # Simpan / update Payment
    payment = Payment.query.filter_by(reservation_id=reservation.id).first()
    if not payment:
        payment = Payment(reservation_id=reservation.id)

    payment.method    = method
    payment.reference = reference_id
    payment.status    = "paid"
    payment.amount    = reservation.total_price

    reservation.status = "paid"

    db.session.add(payment)
    db.session.commit()

    # Bersihkan dari memory
    _sim_transactions.pop(reference_id, None)

    return jsonify(success=True, redirect_url=url_for("customer.dashboard"))