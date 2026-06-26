from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User
from app.services.email_service import send_welcome_email

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
    Sesuai mockup Sign Up: Name, Nomor Handphone, Email Address, Passcode.
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

    if User.query.filter_by(email=email).first():
        flash("Email sudah terdaftar. Silakan login.", "warning")
        return redirect(url_for("auth.login_page"))

    # --- Simpan user baru sebagai customer ---
    new_user = User(
        name=name,
        email=email,
        phone_number=phone_number,
        role="customer",
    )
    new_user.set_password(passcode)

    db.session.add(new_user)
    db.session.commit()

    # --- Kirim welcome email via Resend (gagal kirim tidak boleh gagalkan signup) ---
    try:
        send_welcome_email(to_email=new_user.email, name=new_user.name)
    except Exception as e:
        # Tetap lanjut, cuma log saja
        print(f"[WARN] Gagal mengirim welcome email: {e}")

    login_user(new_user)
    flash(f"Selamat datang, {new_user.name}!", "success")
    return redirect(url_for("customer.dashboard"))


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
