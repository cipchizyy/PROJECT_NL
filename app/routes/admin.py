from functools import wraps
from datetime import date, datetime, timedelta
from app.utils.cloudinary_client import cloudinary_thumbnail_url
from app.services.room_status_service import build_room_status_map
from sqlalchemy.orm import joinedload, selectinload
from time import perf_counter
from flask import current_app

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    abort,
    flash,
    redirect,
    url_for,
    send_file,
    current_app,
)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Room, Reservation, User, Payment, Game  # <-- FIX: tambah Game
from app.services.upload_service import (
    upload_room_image,
    upload_game_image,
)  # <-- FIX: tambah upload_game_image

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
    started_at = perf_counter()

    # 1. Mengambil seluruh room
    query_started_at = perf_counter()

    rooms = Room.query.order_by(Room.room_code).all()

    rooms_duration = (perf_counter() - query_started_at) * 1000

    # 2. Menghitung status room
    query_started_at = perf_counter()

    room_statuses = build_room_status_map(rooms)

    statuses_duration = (perf_counter() - query_started_at) * 1000

    total_rooms = len(rooms)

    available_rooms = sum(
        1 for status in room_statuses.values() if status["state"] == "available"
    )

    active_bookings = sum(
        1 for status in room_statuses.values() if status["state"] == "busy"
    )

    # 3. Menghitung pendapatan hari ini
    today = date.today()
    day_start = datetime.combine(
        today,
        datetime.min.time(),
    )
    day_end = day_start + timedelta(days=1)

    query_started_at = perf_counter()

    daily_revenue = (
        db.session.query(
            db.func.coalesce(
                db.func.sum(Payment.amount),
                0,
            )
        )
        .filter(
            Payment.status == "paid",
            Payment.paid_at >= day_start,
            Payment.paid_at < day_end,
        )
        .scalar()
    )

    revenue_duration = (perf_counter() - query_started_at) * 1000

    daily_revenue = float(daily_revenue or 0)

    total_duration = (perf_counter() - started_at) * 1000

    current_app.logger.warning(
        (
            "DASHBOARD PERF | "
            "rooms=%.1fms | "
            "statuses=%.1fms | "
            "revenue=%.1fms | "
            "total=%.1fms"
        ),
        rooms_duration,
        statuses_duration,
        revenue_duration,
        total_duration,
    )

    return render_template(
        "admin/dashboard.html",
        user=current_user,
        rooms=rooms,
        room_statuses=room_statuses,
        total_rooms=total_rooms,
        available_rooms=available_rooms,
        active_bookings=active_bookings,
        daily_revenue=daily_revenue,
    )


# ── Manage Room (GET) ────────────────────────────────────────
@admin_bp.route("/rooms", methods=["GET"])
@admin_required
def manage_room():
    rooms = Room.query.options(selectinload(Room.games)).order_by(Room.room_code).all()

    all_games = Game.query.order_by(Game.name).all()

    # Jangan memakai Game.to_dict() di sini karena to_dict()
    # menghitung len(game.rooms) dan dapat memicu query tambahan.
    all_games_json = [
        {
            "id": game.id,
            "name": game.name,
            "category": game.category,
            "description": game.description,
            "image_url": cloudinary_thumbnail_url(
                game.image_url,
                240,
                135,
            ),
        }
        for game in all_games
    ]

    return render_template(
        "admin/rooms.html",
        rooms=rooms,
        all_games_json=all_games_json,
    )


# ── Add Room (POST dari modal New Room) ──────────────────────
# FIX: nama fungsi diganti dari add_room -> create_room, karena rooms.html
# manggil {{ url_for('admin.create_room') }} -- kalau nama fungsi beda,
# Flask gak nemu endpoint-nya dan langsung BuildError pas render.
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

    # FIX: field lama "room.room_number" dan "room.tier" DIHAPUS karena
    # kolom itu TIDAK ADA di model Room kamu (yang ada: room_code, name,
    # environment, console_type, dst) -- baris lama itu cuma nempel
    # attribute Python biasa yang gak ke-save ke database, alias bug diam-diam.
    room.room_code = request.form.get("room_code", room.room_code)
    room.name = request.form.get("name", room.name)
    room.environment = request.form.get("environment", room.environment)
    room.console_type = request.form.get("console_type", room.console_type)
    room.price_per_hour = request.form.get("price_per_hour", room.price_per_hour)
    room.room_type = request.form.get("room_type", room.room_type)
    room.seating_type = request.form.get("seating_type") or room.seating_type
    room.description = request.form.get("description") or room.description
    room.status = request.form.get("status", room.status)
    # FIX: baris "room.game_count = ..." DIHAPUS (computed property, read-only)

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
    """
    Daftar reservasi admin dengan search, filter tanggal, eager loading,
    dan pagination.
    """
    search = request.args.get("search", "").strip()
    start_date_str = request.args.get("start_date", "").strip()
    end_date_str = request.args.get("end_date", "").strip()
    page = request.args.get("page", 1, type=int)

    query = (
        Reservation.query.options(
            joinedload(Reservation.room),
            joinedload(Reservation.customer),
        )
        .join(Room)
        .filter(Reservation.status != "pending")
    )

    if search:
        query = query.filter(
            db.or_(
                Reservation.booking_number.ilike(f"%{search}%"),
                Reservation.guest_name.ilike(f"%{search}%"),
                Room.room_code.ilike(f"%{search}%"),
            )
        )

    if start_date_str:
        try:
            start_dt = datetime.strptime(
                start_date_str,
                "%Y-%m-%d",
            )
            query = query.filter(Reservation.start_time >= start_dt)
        except ValueError:
            start_date_str = ""

    if end_date_str:
        try:
            end_dt = datetime.strptime(
                end_date_str,
                "%Y-%m-%d",
            ) + timedelta(days=1)
            query = query.filter(Reservation.start_time < end_dt)
        except ValueError:
            end_date_str = ""

    pagination = query.order_by(Reservation.start_time.desc()).paginate(
        page=page,
        per_page=25,
        error_out=False,
    )

    return render_template(
        "admin/reservations.html",
        reservations=pagination.items,
        pagination=pagination,
        search=search,
        start_date=start_date_str,
        end_date=end_date_str,
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
# @admin_bp.route("/reservations/all", methods=["GET"])
# @admin_required
# def reservations():
#     all_reservations = (
#         Reservation.query.filter(Reservation.status != "pending")
#         .order_by(Reservation.created_at.desc())
#         .all()
#     )
#     return render_template("admin/reservations.html", reservations=all_reservations)


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


@admin_bp.route("/reservations/offline/new", methods=["GET"])
@admin_required
def new_offline_reservation_page():
    """Halaman form input reservasi offline (customer walk-in)."""
    rooms = Room.query.filter(Room.status == "available").order_by(Room.room_code).all()
    return render_template("admin/offline_reservation.html", rooms=rooms)


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

    day_start = datetime.combine(target_date, datetime.min.time())
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

    slots = [
        {
            "start_time": r.start_time.isoformat(),
            "end_time": r.end_time.isoformat(),
        }
        for r in reservations
    ]

    return jsonify(slots=slots)


# FIX: HANYA SATU fungsi create_offline_reservation di seluruh file --
# sebelumnya ada 2 fungsi dengan nama & route sama persis
# ("/reservations/offline", POST), sehingga Flask crash saat register
# blueprint: "View function mapping is overwriting an existing endpoint
# function: admin.create_offline_reservation". Fungsi kedua (versi lama
# tanpa fix Payment & jam tutup) sudah dihapus.
@admin_bp.route("/reservations/offline", methods=["POST"])
@admin_required
def create_offline_reservation():
    """
    Use case: Create Offline Reservation.
    FIX: sebelumnya jsonify(...) -- diganti flash+redirect karena form di
    offline_reservation.html submit biasa (bukan fetch/AJAX).
    """
    room_id = request.form.get("room_id")
    guest_name = request.form.get("guest_name", "").strip()
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
    page = request.args.get("page", 1, type=int)

    pagination = (
        Game.query.options(selectinload(Game.rooms))
        .order_by(Game.created_at.desc())
        .paginate(
            page=page,
            per_page=16,
            error_out=False,
        )
    )

    return render_template(
        "admin/games.html",
        user=current_user,
        games=pagination.items,
        pagination=pagination,
    )


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


def _build_paid_payment_query(start_date_str="", end_date_str=""):
    """
    Membuat query Payment berstatus paid dengan filter tanggal berbasis
    rentang datetime, sehingga index (status, paid_at) dapat digunakan.
    """
    start_date_str = (start_date_str or "").strip()
    end_date_str = (end_date_str or "").strip()

    query = Payment.query.filter(Payment.status == "paid")

    start_dt = None
    end_exclusive = None

    if start_date_str:
        try:
            start_dt = datetime.strptime(
                start_date_str,
                "%Y-%m-%d",
            )
        except ValueError as exc:
            raise ValueError("Format tanggal mulai tidak valid.") from exc

        query = query.filter(Payment.paid_at >= start_dt)

    if end_date_str:
        try:
            end_exclusive = datetime.strptime(
                end_date_str,
                "%Y-%m-%d",
            ) + timedelta(days=1)
        except ValueError as exc:
            raise ValueError("Format tanggal akhir tidak valid.") from exc

        query = query.filter(Payment.paid_at < end_exclusive)

    if start_dt is not None and end_exclusive is not None and start_dt >= end_exclusive:
        raise ValueError("Tanggal akhir tidak boleh lebih awal dari tanggal mulai.")

    return query, start_date_str, end_date_str


def _query_paid_payments(start_date_str, end_date_str):
    """
    Mengambil seluruh pembayaran untuk export PDF.
    Halaman web tidak menggunakan fungsi ini karena sudah dipaginasi.
    """
    query, _, _ = _build_paid_payment_query(
        start_date_str,
        end_date_str,
    )

    return query.order_by(Payment.paid_at.desc()).all()


@admin_bp.route("/report", methods=["GET"])
@admin_required
def create_sales_report():
    start_date_str = request.args.get(
        "start_date",
        "",
    ).strip()

    end_date_str = request.args.get(
        "end_date",
        "",
    ).strip()

    if not start_date_str and not end_date_str:
        today = date.today()

        start_date_str = (today - timedelta(days=30)).isoformat()

    end_date_str = today.isoformat()

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    try:
        query, start_date_str, end_date_str = _build_paid_payment_query(
            start_date_str,
            end_date_str,
        )
    except ValueError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("admin.create_sales_report"))

    # Summary dihitung langsung oleh database untuk seluruh periode.
    stats = query.with_entities(
        db.func.coalesce(
            db.func.sum(Payment.amount),
            0,
        ),
        db.func.count(Payment.id),
        db.func.coalesce(
            db.func.avg(Payment.amount),
            0,
        ),
    ).one()

    total_revenue = float(stats[0] or 0)
    total_transactions = int(stats[1] or 0)
    avg_transaction = float(stats[2] or 0)

    # Tabel hanya mengambil 50 baris per request.
    pagination = query.order_by(Payment.paid_at.desc()).paginate(
        page=page,
        per_page=50,
        error_out=False,
    )

    # Grafik seluruh periode dihitung dengan GROUP BY di database.
    # Ini jauh lebih ringan daripada memuat seluruh objek Payment ke Python.
    payment_date = db.func.date(Payment.paid_at)

    chart_rows = (
        query.with_entities(
            payment_date.label("payment_date"),
            db.func.coalesce(
                db.func.sum(Payment.amount),
                0,
            ).label("daily_total"),
        )
        .group_by(payment_date)
        .order_by(payment_date.asc())
        .all()
    )

    chart_labels = [
        (
            row.payment_date.isoformat()
            if hasattr(row.payment_date, "isoformat")
            else str(row.payment_date)
        )
        for row in chart_rows
    ]

    chart_values = [float(row.daily_total or 0) for row in chart_rows]

    return render_template(
        "admin/sales_report.html",
        payments=pagination.items,
        pagination=pagination,
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
    """
    Export Sales Report ke PDF.

    Rentang tanggal diwajibkan agar server tidak mencoba memuat seluruh
    riwayat pembayaran ke memori pada satu request.
    """
    # Lazy import: ReportLab hanya dimuat saat route PDF dipanggil.
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        LongTable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        TableStyle,
    )
    from reportlab.lib.styles import getSampleStyleSheet

    import io

    start_date_str = (request.args.get("start_date") or "").strip()
    end_date_str = (request.args.get("end_date") or "").strip()

    if not start_date_str or not end_date_str:
        flash(
            "Pilih tanggal mulai dan tanggal akhir sebelum mengunduh PDF.",
            "warning",
        )
        return redirect(url_for("admin.create_sales_report"))

    try:
        payments = _query_paid_payments(
            start_date_str,
            end_date_str,
        )
    except ValueError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("admin.create_sales_report"))

    total_revenue = sum(float(payment.amount) for payment in payments)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
    )
    styles = getSampleStyleSheet()

    elements = [
        Paragraph(
            "Sales Report - Next Level Rent",
            styles["Title"],
        ),
        Spacer(1, 0.5 * cm),
        Paragraph(
            (f"Periode: {start_date_str} " f"s/d {end_date_str}"),
            styles["Normal"],
        ),
        Paragraph(
            f"Total Revenue: Rp {total_revenue:,.0f}",
            styles["Normal"],
        ),
        Spacer(1, 0.5 * cm),
    ]

    table_data = [
        [
            "Tanggal Bayar",
            "Reservasi ID",
            "Metode",
            "Jumlah",
        ]
    ]

    for payment in payments:
        table_data.append(
            [
                (
                    payment.paid_at.strftime("%Y-%m-%d %H:%M")
                    if payment.paid_at
                    else "-"
                ),
                str(payment.reservation_id),
                payment.method or "-",
                f"Rp {float(payment.amount):,.0f}",
            ]
        )

    table = LongTable(
        table_data,
        colWidths=[
            4 * cm,
            5 * cm,
            3 * cm,
            4 * cm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#7c3aed"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "ALIGN",
                    (3, 1),
                    (3, -1),
                    "RIGHT",
                ),
            ]
        )
    )

    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=(f"sales_report_" f"{start_date_str}_" f"{end_date_str}.pdf"),
    )
