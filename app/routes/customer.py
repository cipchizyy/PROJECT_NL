from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
import json

from app.extensions import db
from app.models import Room, Reservation, Payment


customer_bp = Blueprint("customer", __name__, url_prefix="/customer")


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
    return render_template("customer/reservations.html", reservations=reservations)


@customer_bp.route("/reservations", methods=["POST"])
@login_required
def make_reservation():
    room_id = request.form.get("room_id")
    start_time = request.form.get("start_time")
    duration_hours = float(request.form.get("duration_hours", 1))

    room = Room.query.get_or_404(room_id)
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
    reservation_id = request.form.get("reservation_id")
    method = request.form.get("method")

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