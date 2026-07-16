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
from app.models import Room, Reservation, User, Payment, Game               # <-- FIX: tambah Game
from app.services.upload_service import upload_room_image, upload_game_image  # <-- FIX: tambah upload_game_image
from sqlalchemy.exc import IntegrityError

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
    rooms = Room.query.order_by(Room.room_code).all()
    total_rooms = len(rooms)

    # current_status() dihitung real-time per room (available/busy/maintenance/inactive)
    available_rooms = sum(1 for r in rooms if r.current_status()["state"] == "available")
    active_bookings = sum(1 for r in rooms if r.current_status()["state"] == "busy")

    today = date.today()
    todays_payments = Payment.query.filter(
        Payment.status == "paid",
        func.date(Payment.paid_at) == today,
    ).all()
    daily_revenue = sum(float(p.amount) for p in todays_payments)

    return render_template(
        "admin/dashboard.html",
        user=current_user,
        rooms=rooms,
        total_rooms=total_rooms,
        available_rooms=available_rooms,
        active_bookings=active_bookings,
        daily_revenue=daily_revenue,
    )


# ── Manage Room (GET) ────────────────────────────────────────
@admin_bp.route("/rooms", methods=["GET"])
@admin_required
def manage_room():
    """Use case: Manage Room."""
    rooms = Room.query.order_by(Room.room_code).all()

    # FIX: kirim daftar semua game supaya modal "🎮 Games" di rooms.html bisa
    # render checklist assign game per room (dibaca lewat const ALL_GAMES di template)
    all_games = Game.query.order_by(Game.name).all()
    all_games_json = [g.to_dict() for g in all_games]

    return render_template("admin/rooms.html", rooms=rooms, all_games_json=all_games_json)
#add room
@admin_bp.route("/rooms/add", methods=["POST"])
@admin_required
def create_room():
    room_code = request.form.get("room_code")

    # Cek duplikat lebih awal (lebih ramah daripada nunggu IntegrityError)
    if Room.query.filter_by(room_code=room_code).first():
        flash(f"Room dengan kode '{room_code}' sudah ada. Gunakan kode yang berbeda.", "danger")
        return redirect(url_for("admin.manage_room"))

    room = Room(
        room_code=room_code,
        name=request.form.get("name"),
        console_type=request.form.get("console_type"),
        environment=request.form.get("environment", "regular"),
        price_per_hour=request.form.get("price_per_hour"),
        room_type=request.form.get("room_type", "non_smoking"),
        seating_type=request.form.get("seating_type") or None,
        description=request.form.get("description") or None,
        status=request.form.get("status", "available"),
    )

    try:
        db.session.add(room)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f"Room dengan kode '{room_code}' sudah ada. Gunakan kode yang berbeda.", "danger")
        return redirect(url_for("admin.manage_room"))

    # Upload gambar ke Cloudinary kalau ada
    file = request.files.get("image")
    if file and file.filename:
        image_url = upload_room_image(file, room.id)
        room.image_url = image_url
        db.session.commit()

    flash("Room berhasil ditambahkan!", "success")
    return redirect(url_for("admin.manage_room"))
from sqlalchemy.exc import IntegrityError

@admin_bp.route("/rooms/<room_id>/edit", methods=["POST"])
@admin_required
def edit_room(room_id):
    room = Room.query.get_or_404(room_id)

    new_room_code = request.form.get("room_code", room.room_code)

    # Cek duplikat, tapi kecualikan room ini sendiri
    duplicate = Room.query.filter(
        Room.room_code == new_room_code,
        Room.id != room.id
    ).first()
    if duplicate:
        flash(f"Room dengan kode '{new_room_code}' sudah dipakai room lain. Gunakan kode yang berbeda.", "danger")
        return redirect(url_for("admin.manage_room"))

    room.room_code      = new_room_code
    room.name           = request.form.get("name", room.name)
    room.environment    = request.form.get("environment", room.environment)
    room.console_type   = request.form.get("console_type", room.console_type)
    room.price_per_hour = request.form.get("price_per_hour", room.price_per_hour)
    room.room_type      = request.form.get("room_type", room.room_type)
    room.seating_type   = request.form.get("seating_type") or room.seating_type
    room.description    = request.form.get("description") or room.description
    room.status         = request.form.get("status", room.status)

    file = request.files.get("image")
    if file and file.filename:
        image_url = upload_room_image(file, room.id)
        room.image_url = image_url

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f"Room dengan kode '{new_room_code}' sudah dipakai room lain. Gunakan kode yang berbeda.", "danger")
        return redirect(url_for("admin.manage_room"))

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


# ── List Reservasi (halaman 'Reservation' di sidebar admin) ──
@admin_bp.route("/reservations")
@admin_required
def reservation_list():
    """Halaman 'Reservation' di sidebar admin -- tabel lengkap semua reservasi."""
    search = request.args.get("search", "").strip()

    # FIX: transaksi berstatus "pending" (belum dibayar / belum dikonfirmasi)
    # disembunyikan dari Riwayat Transaksi admin -- hanya confirmed/arrived/
    # completed/cancelled yang tampil di sini.
    query = Reservation.query.join(Room).filter(Reservation.status != "pending")

    if search:
        query = query.filter(
            db.or_(
                Reservation.booking_number.ilike(f"%{search}%"),
                Reservation.guest_name.ilike(f"%{search}%"),
                Room.room_code.ilike(f"%{search}%"),
            )
        )

    reservations = query.order_by(Reservation.start_time.desc()).limit(50).all()

    return render_template(
        "admin/reservations.html",
        reservations=reservations,
        search=search,
    )


# FIX: route ini SEBELUMNYA "/reservations/<reservation_id>/arrive" (POST) --
# path itu BENTROK dengan route mark_arrived() di bawah (path identik, endpoint
# beda). Werkzeug mencocokkan ke rule yang didaftarkan lebih dulu (fungsi ini),
# lalu Flask coba panggil reservations(reservation_id=...) padahal fungsi ini
# tidak punya parameter tsb -> TypeError: reservations() got an unexpected
# keyword argument 'reservation_id'.
# Diganti ke path unik "/reservations/all" (GET) supaya tidak bentrok lagi.
# Kalau tidak ada tempat lain yang memanggil endpoint 'admin.reservations',
# fungsi ini sebenarnya duplikat dari reservation_list() di atas dan aman
# untuk dihapus sepenuhnya.
@admin_bp.route("/reservations/all", methods=["GET"])
@admin_required
def reservations():
    all_reservations = (
        Reservation.query
        .filter(Reservation.status != "pending")
        .order_by(Reservation.created_at.desc())
        .all()
    )
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


# =====================================================================
# GANTI route create_offline_reservation() yang lama dengan 3 route ini
# (letakkan di admin.py, posisi sama seperti create_offline_reservation
# yang lama -- setelah reservation_list / sebelum bagian Manage Game)
# =====================================================================


@admin_bp.route("/reservations/offline", methods=["POST"])
@admin_required
def create_offline_reservation():
    """
    Use case: Create Offline Reservation.
    FIX: sebelumnya jsonify(...) -- diganti flash+redirect karena form di
    offline_reservation.html submit biasa (bukan fetch/AJAX).
    """
    room_id     = request.form.get("room_id")
    guest_name  = request.form.get("guest_name", "").strip()
    guest_phone = request.form.get("guest_phone", "").strip() or None
    start_time_str = request.form.get("start_time")

    if not room_id or not guest_name or not start_time_str:
        flash("Room, nama customer, dan waktu mulai wajib diisi.", "danger")
        return redirect(url_for("admin.new_offline_reservation_page"))

    try:
        duration_hours = float(request.form.get("duration_hours", 1))
    except (TypeError, ValueError):
        duration_hours = 1

    if duration_hours <= 0 or duration_hours > 12:
        flash("Durasi harus antara 1-12 jam.", "danger")
        return redirect(url_for("admin.new_offline_reservation_page"))

    try:
        start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        flash("Format waktu mulai tidak valid.", "danger")
        return redirect(url_for("admin.new_offline_reservation_page"))

    # FIX: toko tutup jam 01:00 -- durasi maksimal dibatasi supaya sesi
    # reservasi offline tidak melewati jam tutup. Makin malam start_time,
    # makin pendek durasi maksimal yang diizinkan (mis: mulai 22:00 -> maks 3 jam).
    CLOSING_TIME = time(1, 0)
    if start_time.time() < CLOSING_TIME:
        closing_dt = datetime.combine(start_time.date(), CLOSING_TIME)
    else:
        closing_dt = datetime.combine(start_time.date() + timedelta(days=1), CLOSING_TIME)

    max_allowed_hours = (closing_dt - start_time).total_seconds() / 3600
    if duration_hours > max_allowed_hours:
        flash(
            f"Booking mulai jam {start_time.strftime('%H:%M')} maksimal "
            f"{max_allowed_hours:.0f} jam (tutup jam 01:00).",
            "danger",
        )
        return redirect(url_for("admin.new_offline_reservation_page"))

    end_time = start_time + timedelta(hours=duration_hours)
    room = Room.query.get_or_404(room_id)

    conflict = Reservation.query.filter(
        Reservation.room_id == room.id,
        Reservation.status.in_(["pending", "confirmed"]),
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    ).first()
    if conflict:
        flash(f"Room {room.room_code} sudah dibooking di jam tersebut.", "danger")
        return redirect(url_for("admin.new_offline_reservation_page"))

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

    # FIX: reservasi offline sebelumnya TIDAK PERNAH membuat record Payment,
    # jadi reservation.payment selalu None -> mark_arrived() diam-diam skip
    # -> cash tidak pernah kehitung di daily_revenue / Sales Report walau
    # badge sudah "Arrived". Dibuat "pending" dulu; otomatis "paid" saat
    # admin klik "Mark Arrived".
    payment = Payment(
        reservation_id=reservation.id,
        amount=total_price,
        method="cash",
        status="pending",
    )
    db.session.add(payment)
    db.session.commit()

    flash(f"Reservasi offline untuk {guest_name} berhasil dibuat.", "success")
    return redirect(url_for("admin.reservation_list"))


# FIX: endpoint booked-slots khusus admin, supaya form Reservasi Offline bisa
# menampilkan & mendisable jam yang sudah dibooking -- logikanya disamakan
# persis dengan customer.get_booked_slots (room+tanggal, status pending/confirmed).
@admin_bp.route("/rooms/<string:room_id>/booked-slots", methods=["GET"])
@admin_required
def get_booked_slots_admin(room_id):
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
        func.date(Reservation.start_time) == target_date,
    ).all()

    slots = [
        {
            "start_time": r.start_time.isoformat(),
            "end_time":   r.end_time.isoformat(),
        }
        for r in reservations
    ]

    return jsonify(slots=slots)


@admin_bp.route("/reservations/offline", methods=["POST"])
@admin_required
def create_offline_reservation():
    """
    Use case: Create Offline Reservation.
    FIX: sebelumnya jsonify(...) -- diganti flash+redirect karena form di
    offline_reservation.html submit biasa (bukan fetch/AJAX).
    """
    room_id     = request.form.get("room_id")
    guest_name  = request.form.get("guest_name", "").strip()
    guest_phone = request.form.get("guest_phone", "").strip() or None
    start_time_str = request.form.get("start_time")

    if not room_id or not guest_name or not start_time_str:
        flash("Room, nama customer, dan waktu mulai wajib diisi.", "danger")
        return redirect(url_for("admin.new_offline_reservation_page"))

    try:
        duration_hours = float(request.form.get("duration_hours", 1))
    except (TypeError, ValueError):
        duration_hours = 1

    if duration_hours <= 0 or duration_hours > 12:
        flash("Durasi harus antara 1-12 jam.", "danger")
        return redirect(url_for("admin.new_offline_reservation_page"))

    # FIX: parse string datetime-local ("YYYY-MM-DDTHH:MM") jadi objek datetime
    # yang benar -- sebelumnya string mentah langsung dimasukkan ke kolom
    # DateTime, yang bisa gagal tergantung driver database.
    try:
        start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        flash("Format waktu mulai tidak valid.", "danger")
        return redirect(url_for("admin.new_offline_reservation_page"))

    end_time = start_time + timedelta(hours=duration_hours)
    room = Room.query.get_or_404(room_id)

    # Cegah double booking (room yang sama, slot waktu bentrok)
    conflict = Reservation.query.filter(
        Reservation.room_id == room.id,
        Reservation.status.in_(["pending", "confirmed"]),
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    ).first()
    if conflict:
        flash(f"Room {room.room_code} sudah dibooking di jam tersebut.", "danger")
        return redirect(url_for("admin.new_offline_reservation_page"))

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

    flash(f"Reservasi offline untuk {guest_name} berhasil dibuat.", "success")
    return redirect(url_for("admin.reservation_list"))


@admin_bp.route("/reservations/<reservation_id>/arrive", methods=["POST"])
@admin_required
def mark_arrived(reservation_id):
    """Tombol 'Mark Arrived' di tabel Reservation List."""
    reservation = Reservation.query.get_or_404(reservation_id)
    reservation.is_arrived = True
    reservation.arrived_at = datetime.utcnow()

    # FIX: pembayaran cash baru dianggap lunas saat customer benar-benar
    # datang (Mark Arrived), bukan saat reservasi dibuat -- sebelumnya
    # payment.status untuk cash tetap "pending" selamanya, jadi tidak
    # pernah terhitung di daily_revenue dashboard maupun Sales Report.
    payment = reservation.payment
    if payment and payment.method == "cash" and payment.status != "paid":
        payment.status = "paid"
        payment.paid_at = datetime.utcnow()
        if not payment.amount:
            payment.amount = reservation.total_price

    db.session.commit()

    flash(f"Reservasi #{reservation.booking_number} ditandai sudah datang.", "success")
    return redirect(url_for("admin.reservation_list"))
# ══════════════════════════════════════════════════════════════
# Manage Game
# ══════════════════════════════════════════════════════════════

@admin_bp.route("/games", methods=["GET"])
@admin_required
def manage_game():
    """Use case: Manage Game -> input game oleh admin."""
    # FIX: route decorator diganti dari "/report" -> "/games" (sebelumnya
    # nyasar ke URL sales report, padahal ini halaman Manage Game)
    games = Game.query.order_by(Game.created_at.desc()).all()
    return render_template("admin/games.html", user=current_user, games=games)


@admin_bp.route("/games", methods=["POST"])
@admin_required
def create_game():
    """Use case: Manage Game -> tambah game baru."""
    name = request.form.get("name", "").strip()
    category = request.form.get("category") or None
    description = request.form.get("description", "").strip() or None

    if not name:
        flash("Nama game wajib diisi.", "danger")
        return redirect(url_for("admin.manage_game"))

    # Cek duplikat nama game (case-insensitive) sebelum simpan
    existing_game = Game.query.filter(func.lower(Game.name) == name.lower()).first()
    if existing_game:
        flash(f'Game "{name}" sudah ada di library.', "warning")
        return redirect(url_for("admin.manage_game"))

    game = Game(name=name, category=category, description=description)
    db.session.add(game)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f'Game "{name}" sudah ada di library.', "warning")
        return redirect(url_for("admin.manage_game"))

    file = request.files.get("image")
    if file and file.filename:
        try:
            game.image_url = upload_game_image(file, game.id)
            db.session.commit()
        except ValueError as e:
            flash(str(e), "warning")

    flash(f'Game "{game.name}" berhasil ditambahkan.', "success")
    return redirect(url_for("admin.manage_game"))

# FIX: path & method disamakan dengan yang dipanggil games.js
# (editGameForm.action = `/admin/games/${id}/edit`, method POST)
@admin_bp.route("/games/<game_id>/edit", methods=["POST"])
@admin_required
def update_game(game_id):
    """Use case: Manage Game -> edit game."""
    game = Game.query.get_or_404(game_id)

    name = request.form.get("name", "").strip()
    if not name:
        flash("Nama game wajib diisi.", "danger")
        return redirect(url_for("admin.manage_game"))

    # Cek duplikat nama, tapi abaikan game yang sedang diedit sendiri
    existing_game = Game.query.filter(
        func.lower(Game.name) == name.lower(),
        Game.id != game_id
    ).first()
    if existing_game:
        flash(f'Nama game "{name}" sudah dipakai oleh game lain.', "warning")
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

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f'Nama game "{name}" sudah dipakai oleh game lain.', "warning")
        return redirect(url_for("admin.manage_game"))

    flash(f'Game "{game.name}" berhasil diperbarui.', "success")
    return redirect(url_for("admin.manage_game"))

# FIX: path & method disamakan dengan games.js
# (deleteGameForm.action = `/admin/games/${id}/delete`, method POST)
@admin_bp.route("/games/<game_id>/delete", methods=["POST"])
@admin_required
def delete_game(game_id):
    """Use case: Manage Game -> hapus game. Otomatis lepas dari semua room (pivot)."""
    game = Game.query.get_or_404(game_id)
    name = game.name
    db.session.delete(game)
    db.session.commit()
    flash(f'Game "{name}" berhasil dihapus.', "success")
    return redirect(url_for("admin.manage_game"))


# FIX: jsonify -> flash+redirect, karena form gamesForm di rooms.html
# submit biasa (bukan fetch), bukan endpoint JSON lagi
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


# ══════════════════════════════════════════════════════════════
# Sales Report (route yang tadinya belum pernah dibuat sama sekali,
# makanya BuildError -- sekarang dilengkapi)
# ══════════════════════════════════════════════════════════════

def _build_chart_data(payments):
    """Kelompokkan total revenue per tanggal, untuk Chart.js di sales_report.html."""
    daily_totals = {}
    for p in payments:
        if p.paid_at:
            key = p.paid_at.strftime("%Y-%m-%d")
            daily_totals[key] = daily_totals.get(key, 0) + float(p.amount)
    labels = sorted(daily_totals.keys())
    values = [daily_totals[k] for k in labels]
    return labels, values


def _query_paid_payments(start_date_str, end_date_str):
    """Ambil semua Payment berstatus 'paid', dengan filter rentang tanggal opsional."""
    query = Payment.query.filter_by(status="paid")

    if start_date_str:
        try:
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
            query = query.filter(Payment.paid_at >= start_dt)
        except ValueError:
            pass

    if end_date_str:
        try:
            # end_date inklusif -> geser ke awal hari berikutnya
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Payment.paid_at < end_dt)
        except ValueError:
            pass

    return query.order_by(Payment.paid_at.desc()).all()


@admin_bp.route("/report", methods=["GET"])
@admin_required
def create_sales_report():
    """Halaman Sales Report -- ringkasan + filter tanggal + tabel transaksi."""
    start_date_str = request.args.get("start_date") or ""
    end_date_str = request.args.get("end_date") or ""

    payments = _query_paid_payments(start_date_str, end_date_str)

    total_revenue = sum(float(p.amount) for p in payments)
    total_transactions = len(payments)
    avg_transaction = (total_revenue / total_transactions) if total_transactions else 0

    chart_labels, chart_values = _build_chart_data(payments)

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


@admin_bp.route("/report/download", methods=["GET"])
@admin_required
def download_sales_report():
    """Export Sales Report ke PDF pakai reportlab."""
    start_date_str = request.args.get("start_date") or ""
    end_date_str = request.args.get("end_date") or ""

    payments = _query_paid_payments(start_date_str, end_date_str)
    total_revenue = sum(float(p.amount) for p in payments)

    import io
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Sales Report - Next Level Rent", styles["Title"]),
        Spacer(1, 0.5 * cm),
        Paragraph(f"Periode: {start_date_str or 'Semua'} s/d {end_date_str or 'Semua'}", styles["Normal"]),
        Paragraph(f"Total Revenue: Rp {total_revenue:,.0f}", styles["Normal"]),
        Spacer(1, 0.5 * cm),
    ]

    # FIX: baris "for p in payments:" sebelumnya ada di kolom 0 (tidak
    # ter-indent), sehingga keluar dari body function ini. Akibatnya baris
    # "return send_file(...)" di bawah juga ikut keluar dari function ->
    # SyntaxError: 'return' outside function saat di-deploy ke Vercel.
    # Sekarang di-indent kembali supaya tetap berada di dalam
    # download_sales_report().
    table_data = [["Tanggal Bayar", "Reservasi ID", "Metode", "Jumlah"]]
    for p in payments:
        table_data.append([
            p.paid_at.strftime("%Y-%m-%d %H:%M") if p.paid_at else "-",
            p.reservation.booking_number if p.reservation else "-",
            p.method or "-",
            f"Rp {float(p.amount):,.0f}",
        ])

    table = Table(table_data, colWidths=[4 * cm, 5 * cm, 3 * cm, 4 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7c3aed")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="sales_report.pdf",
    )
