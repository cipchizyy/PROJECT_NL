from functools import wraps
from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Room, Reservation, User, Payment
from app.services.upload_service import upload_room_image

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    """Pastikan hanya role=admin yang bisa akses route ini."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html", user=current_user)


@admin_bp.route("/rooms", methods=["GET"])
@admin_required
def manage_room():
    """Use case: Manage Room."""
    rooms = Room.query.all()
    return render_template("admin/rooms.html", rooms=rooms)


@admin_bp.route("/rooms", methods=["POST"])
@admin_required
def create_room():
    name = request.form.get("name")
    console_type = request.form.get("console_type")
    price_per_hour = request.form.get("price_per_hour")

    room = Room(name=name, console_type=console_type, price_per_hour=price_per_hour)
    db.session.add(room)
    db.session.commit()

    # Upload foto room ke Cloudinary kalau ada
    file = request.files.get("image")
    if file:
        image_url = upload_room_image(file, room.id)
        room.image_url = image_url
        db.session.commit()

    return jsonify({"success": True, "room": room.to_dict()}), 201


@admin_bp.route("/reservations/<reservation_id>", methods=["PUT"])
@admin_required
def update_reservation(reservation_id):
    """Use case: Update Reservation (<<extend>> Manage Room)."""
    reservation = Reservation.query.get_or_404(reservation_id)

    reservation.status = request.form.get("status", reservation.status)
    db.session.commit()

    return jsonify({"success": True, "reservation": reservation.to_dict()})


@admin_bp.route("/reservations/<reservation_id>", methods=["DELETE"])
@admin_required
def delete_reservation(reservation_id):
    """Use case: Delete Reservation (<<extend>> Manage Room)."""
    reservation = Reservation.query.get_or_404(reservation_id)
    db.session.delete(reservation)
    db.session.commit()

    return jsonify({"success": True})


@admin_bp.route("/reservations/offline", methods=["POST"])
@admin_required
def create_offline_reservation():
    """Use case: Create Offline Reservation (untuk walk-in customer)."""
    room_id = request.form.get("room_id")
    guest_name = request.form.get("guest_name")
    guest_phone = request.form.get("guest_phone")
    start_time = request.form.get("start_time")
    duration_hours = float(request.form.get("duration_hours", 1))

    room = Room.query.get_or_404(room_id)
    total_price = float(room.price_per_hour) * duration_hours

    reservation = Reservation(
        room_id=room.id,
        guest_name=guest_name,
        guest_phone=guest_phone,
        start_time=start_time,
        duration_hours=duration_hours,
        total_price=total_price,
        source="offline",
        status="confirmed",
        created_by_admin_id=current_user.id,
    )
    db.session.add(reservation)
    db.session.commit()

    return jsonify({"success": True, "reservation": reservation.to_dict()}), 201


@admin_bp.route("/sales-report", methods=["GET"])
@admin_required
def create_sales_report():
    """Use case: Create Sales Report (agregat dari Payment)."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    query = Payment.query.filter_by(status="paid")
    # TODO: filter berdasarkan rentang tanggal start_date - end_date

    payments = query.all()
    total_revenue = sum(float(p.amount) for p in payments)
    total_transactions = len(payments)

    return render_template(
        "admin/sales_report.html",
        payments=payments,
        total_revenue=total_revenue,
        total_transactions=total_transactions,
    )
