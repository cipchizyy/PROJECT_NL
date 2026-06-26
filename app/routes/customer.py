from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Room, Reservation, Payment

customer_bp = Blueprint("customer", __name__, url_prefix="/customer")


@customer_bp.route("/dashboard")
@login_required
def dashboard():
    """CUST-Dashboard, sesuai label di mockup."""
    return render_template("customer/dashboard.html", user=current_user)


@customer_bp.route("/rooms")
@login_required
def view_room_schedule():
    """Use case: View Room Schedule + Choose Available Room."""
    selected_env = request.args.get("environment", "regular")

    rooms = (
        Room.query.filter_by(environment=selected_env)
        .filter(Room.status != "inactive")
        .order_by(Room.room_code.asc())
        .all()
    )

    # Hitung status real-time (available/busy + sisa menit) sekali di sini,
    # supaya template tidak perlu panggil method berulang-ulang per render.
    rooms_with_status = [(room, room.current_status()) for room in rooms]

    return render_template(
        "customer/rooms.html",
        rooms_with_status=rooms_with_status,
        selected_env=selected_env,
        current_user=current_user,
    )


@customer_bp.route("/reservations", methods=["GET"])
@login_required
def view_reservation():
    """Use case: View Reservation (milik customer yang login)."""
    reservations = (
        Reservation.query.filter_by(customer_id=current_user.id)
        .order_by(Reservation.start_time.desc())
        .all()
    )
    return render_template("customer/reservations.html", reservations=reservations)


@customer_bp.route("/reservations", methods=["POST"])
@login_required
def make_reservation():
    """Use case: Make Room Reservation -> lanjut ke Create Payment."""
    room_id = request.form.get("room_id")
    start_time = request.form.get("start_time")
    duration_hours = float(request.form.get("duration_hours", 1))

    room = Room.query.get_or_404(room_id)
    # TODO: hitung end_time dari start_time + duration, cek bentrok jadwal, dst.

    total_price = float(room.price_per_hour) * duration_hours

    reservation = Reservation(
        room_id=room.id,
        customer_id=current_user.id,
        start_time=start_time,
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
    """Use case: Create Payment, generalisasi CASH / CASHLESS."""
    reservation_id = request.form.get("reservation_id")
    method = request.form.get("method")  # "cash" atau "cashless"

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