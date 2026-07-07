from functools import wraps
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, abort
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


# ── Dashboard ────────────────────────────────────────────────
@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html", user=current_user)


# ── Manage Room (GET) ────────────────────────────────────────
@admin_bp.route("/rooms", methods=["GET"])
@admin_required
def manage_room():
    tier = request.args.get("tier")  # filter dari tab: regular, regular_pro, vip

    if tier:
        # Ubah "regular_pro" → "Regular Pro" untuk query ke DB
        tier_label = tier.replace("_", " ").title()
        rooms = Room.query.filter_by(tier=tier_label).all()
    else:
        rooms = Room.query.all()

    return render_template("admin/manage_room.html", rooms=rooms)


# ── Add Room (POST dari modal New Room) ──────────────────────
@admin_bp.route("/rooms/add", methods=["POST"])
@admin_required
def add_room():
    room_number   = request.form.get("room_number")
    tier          = request.form.get("tier")
    price_per_hour = request.form.get("price_per_hour")
    game_count    = request.form.get("game_count", 0)
    smoking_label = request.form.get("smoking_label")
    seating_type  = request.form.get("seating_type")

    room = Room(
        room_number=room_number,
        tier=tier,
        price_per_hour=price_per_hour,
        game_count=game_count,
        smoking_label=smoking_label,
        seating_type=seating_type,
    )
    db.session.add(room)
    db.session.commit()

    # Upload gambar ke Cloudinary kalau ada
    file = request.files.get("image")
    if file and file.filename:
        image_url = upload_room_image(file, room.id)
        room.image_url = image_url
        db.session.commit()

    flash("Room berhasil ditambahkan!", "success")
    return redirect(url_for("admin.manage_room"))


# ── Edit Room (POST dari modal Edit) ────────────────────────
@admin_bp.route("/rooms/<room_id>/edit", methods=["POST"])
@admin_required
def edit_room(room_id):
    room = Room.query.get_or_404(room_id)

    room.room_number   = request.form.get("room_number", room.room_number)
    room.tier          = request.form.get("tier", room.tier)
    room.price_per_hour = request.form.get("price_per_hour", room.price_per_hour)
    room.game_count    = request.form.get("game_count", room.game_count)
    room.smoking_label = request.form.get("smoking_label", room.smoking_label)
    room.seating_type  = request.form.get("seating_type", room.seating_type)

    # Ganti gambar kalau ada upload baru
    file = request.files.get("image")
    if file and file.filename:
        image_url = upload_room_image(file, room.id)
        room.image_url = image_url

    db.session.commit()
    flash("Room berhasil diupdate!", "success")
    return redirect(url_for("admin.manage_room"))


# ── Delete Room ──────────────────────────────────────────────
@admin_bp.route("/rooms/<room_id>/delete", methods=["POST"])
@admin_required
def delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    flash("Room berhasil dihapus.", "success")
    return redirect(url_for("admin.manage_room"))


# ── Detail Room ──────────────────────────────────────────────
@admin_bp.route("/rooms/<room_id>")
@admin_required
def room_detail(room_id):
    room = Room.query.get_or_404(room_id)
    return render_template("admin/room_detail.html", room=room)


# ── Reservations ─────────────────────────────────────────────
@admin_bp.route("/reservations")
@admin_required
def reservations():
    all_reservations = Reservation.query.order_by(Reservation.created_at.desc()).all()
    return render_template("admin/reservations.html", reservations=all_reservations)


@admin_bp.route("/reservations/<reservation_id>", methods=["PUT"])
@admin_required
def update_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    reservation.status = request.form.get("status", reservation.status)
    db.session.commit()
    return jsonify({"success": True, "reservation": reservation.to_dict()})


@admin_bp.route("/reservations/<reservation_id>", methods=["DELETE"])
@admin_required
def delete_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    db.session.delete(reservation)
    db.session.commit()
    return jsonify({"success": True})


@admin_bp.route("/reservations/offline", methods=["POST"])
@admin_required
def create_offline_reservation():
    room_id        = request.form.get("room_id")
    guest_name     = request.form.get("guest_name")
    guest_phone    = request.form.get("guest_phone")
    start_time     = request.form.get("start_time")
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


# ── Generate Report ──────────────────────────────────────────
@admin_bp.route("/report")
@admin_required
def generate_report():
    start_date = request.args.get("start_date")
    end_date   = request.args.get("end_date")

    query = Payment.query.filter_by(status="paid")
    # TODO: tambah filter tanggal kalau start_date / end_date ada

    payments = query.all()
    total_revenue      = sum(float(p.amount) for p in payments)
    total_transactions = len(payments)

    return render_template(
        "admin/generate_report.html",
        payments=payments,
        total_revenue=total_revenue,
        total_transactions=total_transactions,
    )