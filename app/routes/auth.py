from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, OtpCode
from app.services.email_service import send_welcome_email, send_otp_email

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/", methods=["GET"])
def login_page():
    """
    Halaman gabungan Login & Sign Up (sesuai mockup: satu kartu dengan tab
    LOGIN / SIGN UP). Kalau sudah login, langsung redirect ke dashboard masing-masing.
    """
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard" if current_user.is_admin else "customer.dashboard"))
    return render_template("auth/login.html")


@auth_bp.route("/signup", methods=["POST"])
def signup():
    """
    Step 1 dari Sign Up: simpan data user (belum aktif/terverifikasi),
    lalu kirim OTP ke email dan redirect ke halaman verifikasi.
    """
    name = request.form.get("name", "").strip()
    phone_number = request.form.get("phone_number", "").strip()
    email = request.form.get("email", "").strip().lower()
    passcode = request.form.get("passcode", "")

    # --- Validasi dasar ---
    if not all([name, phone_number, email, passcode]):
        flash("Semua field wajib diisi.", "danger")
        return redirect(url_for("auth.login_page"))

    if len(passcode) < 6:
        flash("Passcode minimal 6 karakter.", "danger")
        return redirect(url_for("auth.login_page"))

    existing_user = User.query.filter_by(email=email).first()
    if existing_user and existing_user.is_email_verified:
        flash("Email sudah terdaftar. Silakan login.", "warning")
        return redirect(url_for("auth.login_page"))

    if existing_user and not existing_user.is_email_verified:
        # User sebelumnya pernah signup tapi belum verifikasi -> update datanya & kirim OTP baru
        existing_user.name = name
        existing_user.phone_number = phone_number
        existing_user.set_password(passcode)
        db.session.commit()
        user = existing_user
    else:
        # --- Simpan user baru sebagai customer, belum terverifikasi ---
        user = User(
            name=name,
            email=email,
            phone_number=phone_number,
            role="customer",
            is_email_verified=False,
        )
        user.set_password(passcode)
        db.session.add(user)
        db.session.commit()

    # --- Generate & kirim OTP via Resend ---
    otp = OtpCode.create_for_user(user_id=user.id, email=user.email, purpose="email_verification")

    try:
        send_otp_email(to_email=user.email, name=user.name, otp_code=otp.code)
    except Exception as e:
        print(f"[WARN] Gagal mengirim OTP email: {e}")
        # Jangan return di sini, tetap lanjut
        flash("Kode verifikasi gagal dikirim via email, tapi kamu tetap bisa coba verifikasi.", "warning")

    # Simpan user_id sementara di session untuk dipakai di halaman verifikasi
    session["pending_verification_user_id"] = user.id

    flash(f"Kode verifikasi telah dikirim ke {user.email}.", "info")
    return redirect(url_for("auth.verify_otp_page"))


@auth_bp.route("/verify-otp", methods=["GET"])
def verify_otp_page():
    """Halaman input OTP 6 digit, sesuai flow setelah Sign Up."""
    user_id = session.get("pending_verification_user_id")
    if not user_id:
        flash("Sesi verifikasi tidak ditemukan, silakan sign up ulang.", "warning")
        return redirect(url_for("auth.login_page"))

    user = User.query.get(user_id)
    if not user:
        session.pop("pending_verification_user_id", None)
        return redirect(url_for("auth.login_page"))

    return render_template("emails/verify_otp.html", email=user.email)


@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    """Step 2 dari Sign Up: validasi OTP yang diinput user."""
    user_id = session.get("pending_verification_user_id")
    if not user_id:
        flash("Sesi verifikasi tidak ditemukan, silakan sign up ulang.", "warning")
        return redirect(url_for("auth.login_page"))

    user = User.query.get(user_id)
    if not user:
        session.pop("pending_verification_user_id", None)
        return redirect(url_for("auth.login_page"))

    # Gabungkan 6 input digit terpisah jadi satu kode
    input_code = "".join(
        request.form.get(f"digit{i}", "").strip() for i in range(1, 7)
    )

    if len(input_code) != 6 or not input_code.isdigit():
        flash("Kode OTP harus 6 digit angka.", "danger")
        return redirect(url_for("auth.verify_otp_page"))

    latest_otp = (
        OtpCode.query.filter_by(user_id=user.id, purpose="email_verification", is_used=False)
        .order_by(OtpCode.created_at.desc())
        .first()
    )

    if not latest_otp or not latest_otp.is_valid(input_code):
        flash("Kode OTP salah atau sudah kedaluwarsa.", "danger")
        return redirect(url_for("auth.verify_otp_page"))

    # --- OTP valid: aktifkan akun ---
    latest_otp.is_used = True
    user.is_email_verified = True
    db.session.commit()

    session.pop("pending_verification_user_id", None)

    try:
        send_welcome_email(to_email=user.email, name=user.name)
    except Exception as e:
        print(f"[WARN] Gagal mengirim welcome email: {e}")

    # Sesudah
    login_user(user)
    flash(f"Email berhasil diverifikasi. Selamat datang, {user.name}!", "success")
    if user.is_admin:
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("customer.dashboard"))


@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    """Kirim ulang kode OTP kalau user belum menerima/kode kedaluwarsa."""
    user_id = session.get("pending_verification_user_id")
    if not user_id:
        flash("Sesi verifikasi tidak ditemukan, silakan sign up ulang.", "warning")
        return redirect(url_for("auth.login_page"))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for("auth.login_page"))

    otp = OtpCode.create_for_user(user_id=user.id, email=user.email, purpose="email_verification")

    try:
        send_otp_email(to_email=user.email, name=user.name, otp_code=otp.code)
        flash("Kode OTP baru telah dikirim.", "success")
    except Exception as e:
        print(f"[WARN] Gagal mengirim ulang OTP: {e}")
        flash("Gagal mengirim ulang kode OTP.", "danger")

    return redirect(url_for("auth.verify_otp_page"))


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Sesuai mockup Login: Email Address + Passcode.
    """
    email = request.form.get("email", "").strip().lower()
    passcode = request.form.get("passcode", "")

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(passcode):
        flash("Email atau passcode salah.", "danger")
        return redirect(url_for("auth.login_page"))

    if not user.is_email_verified:
        # Belum verifikasi -> kirim ulang ke flow OTP, jangan biarkan login
        session["pending_verification_user_id"] = user.id
        otp = OtpCode.create_for_user(user_id=user.id, email=user.email, purpose="email_verification")
        try:
            send_otp_email(to_email=user.email, name=user.name, otp_code=otp.code)
        except Exception as e:
            print(f"[WARN] Gagal mengirim OTP email: {e}")
        flash("Email belum diverifikasi. Kode verifikasi baru telah dikirim.", "warning")
        return redirect(url_for("auth.verify_otp_page"))

    if not user.is_active:
        flash("Akun Anda tidak aktif. Hubungi Admin.", "danger")
        return redirect(url_for("auth.login_page"))

    login_user(user)
    flash(f"Selamat datang kembali, {user.name}!", "success")

    if user.is_admin:
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("customer.dashboard"))


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Anda telah logout.", "info")
    return redirect(url_for("auth.login_page"))