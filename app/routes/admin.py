import io
from functools import wraps
from datetime import date, datetime, timedelta

from sqlalchemy import func
from flask import (
    Blueprint, render_template, request, jsonify, abort,
    flash, redirect, url_for, send_file,
    )
from flask_login import login_required, current_user
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from app.extensions import db
from app.models import Room, Reservation, User, Payment, game
from app.models.game import Game
from app.services.upload_service import upload_room_image, upload_game_image

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
    # Stat cards
    total_rooms     = Room.query.count()
    available_rooms = Room.query.filter_by(status="available").count()
    active_bookings = Reservation.query.filter_by(status="confirmed").count()

    # Daily revenue hari ini
    today = date.today()
    daily_revenue = db.session.query(func.sum(Reservation.total_price)).filter(
        func.date(Reservation.created_at) == today,
        Reservation.status.in_(["confirmed", "completed"])
    ).scalar()
    daily_revenue = float(daily_revenue or 0)

    # Room grid — semua room kecuali inactive, limit 6 untuk dashboard
    rooms = Room.query.filter(
        Room.status != 'inactive'
    ).order_by(Room.room_code).limit(6).all()

    return render_template(
        "admin/dashboard.html",
        total_rooms=total_rooms,
        available_rooms=available_rooms,
        active_bookings=active_bookings,
        daily_revenue=daily_revenue,
        rooms=rooms,
    )


@admin_bp.route("/rooms", methods=["GET"])
@admin_required
def manage_room():
    rooms = Room.query.order_by(Room.created_at.desc()).all()
    
    all_games = Game.query.order_by(Game.name).all()        # <-- pastikan baris ini ADA
    all_games_json = [g.to_dict() for g in all_games]         # <-- pastikan baris ini ADA
    
    return render_template(
        "admin/rooms.html",
        user=current_user,
        rooms=rooms,
        all_games_json=all_games_json,                        # <-- pastikan parameter ini ADA
    )


@admin_bp.route("/rooms", methods=["POST"])
@admin_required
def create_room():
    room = Room(
        room_code=request.form.get("room_code"),
        name=request.form.get("name"),
        console_type=request.form.get("console_type"),
        environment=request.form.get("environment", "regular"),
        price_per_hour=request.form.get("price_per_hour"),
        room_type=request.form.get("room_type", "non_smoking"),
        seating_type=request.form.get("seating_type") or None,
        description=request.form.get("description") or None,
        status=request.form.get("status", "available"),
    )
    db.session.add(room)
    db.session.commit()

    # Upload foto room ke Cloudinary kalau ada
    file = request.files.get("image")
    if file and file.filename:
        image_url = upload_room_image(file, room.id)
        room.image_url = image_url
        db.session.commit()

    flash(f"Room '{room.room_code}' berhasil ditambahkan.", "success")
    return redirect(url_for("admin.manage_room"))


@admin_bp.route("/rooms/<string:room_id>/edit", methods=["POST"])
@admin_required
def edit_room(room_id):
    """Use case: Update Room (bagian dari Manage Room)."""
    room = Room.query.get_or_404(room_id)

    room.room_code = request.form.get("room_code", room.room_code)
    room.name = request.form.get("name", room.name)
    room.console_type = request.form.get("console_type", room.console_type)
    room.environment = request.form.get("environment", room.environment)
    room.price_per_hour = request.form.get("price_per_hour", room.price_per_hour)
    room.room_type = request.form.get("room_type", room.room_type)
    room.seating_type = request.form.get("seating_type") or room.seating_type
    room.description = request.form.get("description") or room.description
    room.status = request.form.get("status", room.status)

    file = request.files.get("image")
    if file and file.filename:
        image_url = upload_room_image(file, room.id)
        room.image_url = image_url

    db.session.commit()
    flash(f"Room '{room.room_code}' berhasil diperbarui.", "success")
    return redirect(url_for("admin.manage_room"))


@admin_bp.route("/rooms/<string:room_id>/delete", methods=["POST"])
@admin_required
def delete_room(room_id):
    """Use case: Delete Room (bagian dari Manage Room)."""
    room = Room.query.get_or_404(room_id)
    code = room.room_code
    db.session.delete(room)
    db.session.commit()
    flash(f"Room '{code}' berhasil dihapus.", "success")
    return redirect(url_for("admin.manage_room"))


@admin_bp.route("/reservations", methods=["GET"])
@admin_required
def reservation_list():
    """Halaman 'Reservation' di sidebar admin -- tabel lengkap semua reservasi."""
    search = request.args.get("search", "").strip()
    start_date_str = request.args.get("start_date", "").strip()
    end_date_str = request.args.get("end_date", "").strip()

    query = Reservation.query.join(Room)

    if search:
        query = query.filter(
            db.or_(
                Reservation.booking_number.ilike(f"%{search}%"),
                Reservation.guest_name.ilike(f"%{search}%"),
                Room.room_code.ilike(f"%{search}%"),
            )
        )

    # Filter rentang tanggal berdasarkan start_time reservasi.
    # end_date diperlakukan inklusif (seluruh hari itu ikut), sama seperti
    # pola yang sudah dipakai di _query_paid_payments.
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            query = query.filter(Reservation.start_time >= start_date)
        except ValueError:
            start_date_str = ""

    if end_date_str:
        try:
            end_date_exclusive = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Reservation.start_time < end_date_exclusive)
        except ValueError:
            end_date_str = ""

    reservations = query.order_by(Reservation.start_time.desc()).limit(50).all()

    return render_template(
        "admin/reservations.html",
        reservations=reservations,
        search=search,
        start_date=start_date_str,
        end_date=end_date_str,
    )


@admin_bp.route("/reservations/<reservation_id>/arrive", methods=["POST"])
@admin_required
def mark_arrived(reservation_id):
    """Tandai customer sudah check-in fisik di lokasi (badge 'Arrived')."""
    reservation = Reservation.query.get_or_404(reservation_id)
    reservation.is_arrived = True
    reservation.arrived_at = datetime.utcnow()
    db.session.commit()

    flash(f"Reservasi {reservation.booking_number} ditandai Arrived.", "success")
    return redirect(url_for("admin.reservation_list"))


@admin_bp.route("/reservations/offline/new", methods=["GET"])
@admin_required
def new_offline_reservation_page():
    """
    Halaman form Create Offline Reservation, dibuka lewat tombol (+) pink
    di Reservation List (sesuai mockup).
    """
    rooms = Room.query.filter_by(status="available").order_by(Room.room_code).all()
    return render_template("admin/offline_reservation.html", rooms=rooms)


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
    start_time_raw = request.form.get("start_time")
    duration_hours = float(request.form.get("duration_hours", 1))

    room = Room.query.get_or_404(room_id)

    # Input dari <input type="datetime-local"> formatnya "YYYY-MM-DDTHH:MM"
    start_time = datetime.strptime(start_time_raw, "%Y-%m-%dT%H:%M")
    end_time = start_time + timedelta(hours=duration_hours)

    total_price = float(room.price_per_hour) * duration_hours

    reservation = Reservation(
        room_id=room.id,
        guest_name=guest_name,
        guest_phone=guest_phone,
        start_time=start_time,
        end_time=end_time,
        duration_hours=duration_hours,
        total_price=total_price,
        source="offline",
        status="confirmed",
        created_by_admin_id=current_user.id,
    )
    db.session.add(reservation)
    db.session.commit()

    flash(f"Reservasi offline {reservation.booking_number} untuk {guest_name} berhasil dibuat.", "success")
    return redirect(url_for("admin.reservation_list"))


@admin_bp.route("/games", methods=["GET"])
@admin_required
def manage_game():
    """Use case: Manage Game -> input game oleh admin."""
    games = Game.query.order_by(Game.created_at.desc()).all()
    return render_template("admin/games.html", user=current_user, active_page="games", games=games)


@admin_bp.route("/games", methods=["POST"])
@admin_required
def create_game():
    name = request.form.get("name", "").strip()
    category = request.form.get("category") or None
    description = request.form.get("description", "").strip() or None

    if not name:
        flash("Nama game wajib diisi.", "danger")
        return redirect(url_for("admin.manage_game"))

    game = Game(name=name, category=category, description=description)
    db.session.add(game)
    db.session.commit()

    file = request.files.get("image")
    if file and file.filename:
        try:
            game.image_url = upload_game_image(file, game.id)
            db.session.commit()
        except ValueError as e:
            flash(str(e), "warning")

    flash(f'Game "{game.name}" berhasil ditambahkan.', "success")
    return redirect(url_for("admin.manage_game"))


@admin_bp.route("/games/<game_id>", methods=["GET"])
@admin_required
def get_game(game_id):
    """Ambil detail satu game (dipakai untuk mengisi form edit)."""
    game = Game.query.get_or_404(game_id)
    return jsonify({"success": True, "game": game.to_dict()})


@admin_bp.route("/games/<game_id>/edit", methods=["POST"])
@admin_required
def update_game(game_id):
    game = Game.query.get_or_404(game_id)

    name = request.form.get("name", "").strip()
    if not name:
        flash("Nama game wajib diisi.", "danger")
        return redirect(url_for("admin.manage_game"))

    game.name = name
    game.category = request.form.get("category") or None
    game.description = request.form.get("description", "").strip() or None

    file = request.files.get("image")
    if file and file.filename:
        try:
            game.image_url = upload_game_image(file, game.id)
        except ValueError as e:
            flash(str(e), "warning")

    db.session.commit()
    flash(f'Game "{game.name}" berhasil diperbarui.', "success")
    return redirect(url_for("admin.manage_game"))


@admin_bp.route("/games/<game_id>/delete", methods=["POST"])
@admin_required
def delete_game(game_id):
    game = Game.query.get_or_404(game_id)
    name = game.name
    db.session.delete(game)
    db.session.commit()
    flash(f'Game "{name}" berhasil dihapus.', "success")
    return redirect(url_for("admin.manage_game"))


@admin_bp.route("/rooms/<room_id>/games", methods=["GET"])
@admin_required
def get_room_games(room_id):
    """
    Use case: Manage Game -> Assign Game to Room.
    Mengembalikan semua game yang ada, ditandai mana yang sudah terpasang di room ini.
    """
    room = Room.query.get_or_404(room_id)
    assigned_ids = {g.id for g in room.games}
    all_games = Game.query.order_by(Game.name).all()

    return jsonify({
        "success": True,
        "room": room.to_dict(),
        "games": [
            {**g.to_dict(), "assigned": g.id in assigned_ids}
            for g in all_games
        ],
    })


@admin_bp.route("/rooms/<room_id>/games", methods=["POST"])
@admin_required
def set_room_games(room_id):
    """
    Use case: Manage Game -> Assign Game to Room.
    Menyimpan daftar game yang dicentang admin untuk room tertentu (replace semua).
    """
    room = Room.query.get_or_404(room_id)
    game_ids = request.form.getlist("game_ids")

    games = Game.query.filter(Game.id.in_(game_ids)).all() if game_ids else []
    room.games = games
    db.session.commit()

    flash(f'Daftar game untuk room "{room.room_code}" berhasil disimpan.', "success")
    return redirect(url_for("admin.manage_room"))


def _query_paid_payments(start_date_str, end_date_str):
    """
    Helper bersama: ambil semua Payment berstatus 'paid' dengan filter rentang
    tanggal opsional, dipakai baik oleh halaman HTML maupun endpoint download PDF
    supaya datanya selalu konsisten.

    end_date diperlakukan inklusif (seluruh hari itu ikut terhitung) dengan
    membandingkan '< end_date + 1 hari', bukan '<= end_date 00:00'.
    """
    query = Payment.query.filter_by(status="paid")

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            query = query.filter(Payment.paid_at >= start_date)
        except ValueError:
            start_date_str = None

    if end_date_str:
        try:
            end_date_exclusive = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Payment.paid_at < end_date_exclusive)
        except ValueError:
            end_date_str = None

    payments = query.order_by(Payment.paid_at.desc()).all()
    return payments, start_date_str, end_date_str


@admin_bp.route("/sales-report", methods=["GET"])
@admin_required
def create_sales_report():
    """Use case: Create Sales Report (agregat dari Payment)."""
    start_date_str = request.args.get("start_date")
    end_date_str   = request.args.get("end_date")

    payments, start_date_str, end_date_str = _query_paid_payments(start_date_str, end_date_str)

    total_revenue      = sum(float(p.amount) for p in payments)
    total_transactions = len(payments)
    avg_transaction     = (total_revenue / total_transactions) if total_transactions else 0.0

    # Rekap revenue per hari, dipakai untuk chart di halaman report
    revenue_by_day = {}
    for p in payments:
        if not p.paid_at:
            continue
        day_key = p.paid_at.strftime("%Y-%m-%d")
        revenue_by_day[day_key] = revenue_by_day.get(day_key, 0) + float(p.amount)

    chart_labels = sorted(revenue_by_day.keys())
    chart_values = [revenue_by_day[d] for d in chart_labels]

    return render_template(
        "admin/sales_report.html",
        payments=payments,
        total_revenue=total_revenue,
        total_transactions=total_transactions,
        avg_transaction=avg_transaction,
        start_date=start_date_str,
        end_date=end_date_str,
        chart_labels=chart_labels,
        chart_values=chart_values,
    )


@admin_bp.route("/reports", methods=["GET"], endpoint="sales_report")
@admin_required
def sales_report_alias():
    """
    Alias kompatibilitas: kalau ada template lain (selain admin/sidebar.html)
    yang memanggil url_for('admin.sales_report'), redirect ke endpoint asli
    'admin.create_sales_report' supaya tidak BuildError, tanpa mengubah
    nama endpoint utama yang sudah dipakai admin/sidebar.html.
    """
    return redirect(url_for("admin.create_sales_report", **request.args))


@admin_bp.route("/sales-report/download", methods=["GET"])
@admin_required
def download_sales_report():
    """Generate Sales Report yang sama persis, dikirim sebagai file PDF."""
    start_date_str = request.args.get("start_date")
    end_date_str   = request.args.get("end_date")

    payments, start_date_str, end_date_str = _query_paid_payments(start_date_str, end_date_str)

    total_revenue      = sum(float(p.amount) for p in payments)
    total_transactions = len(payments)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Sales Report", styles["Title"]))
    periode = f"{start_date_str or 'Semua'} s/d {end_date_str or 'Semua'}"
    story.append(Paragraph(f"Periode: {periode}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"Total Transaksi: {total_transactions}", styles["Normal"]))
    story.append(Paragraph(f"Total Revenue: Rp {total_revenue:,.0f}", styles["Normal"]))
    story.append(Spacer(1, 16))

    table_data = [["Tanggal Bayar", "Reservasi ID", "Metode", "Jumlah"]]
    for p in payments:
        table_data.append([
            p.paid_at.strftime("%Y-%m-%d %H:%M") if p.paid_at else "-",
            str(p.reservation_id),
            p.method or "-",
            f"Rp {float(p.amount):,.0f}",
        ])

    table = Table(table_data, colWidths=[4 * cm, 5 * cm, 3 * cm, 4 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)

    filename = f"sales_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )