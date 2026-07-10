from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models.user import User
from app.services.email_service import send_welcome_email
from app.services.email_service import (
    send_otp_email,
    send_welcome_email,
    send_password_reset_email,
)

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
@auth_bp.route("/signup", methods=["POST"])
def signup():
    name = request.form.get("name", "").strip()
    phone_number = request.form.get("phone_number", "").strip()
    email = request.form.get("email", "").strip().lower()
    passcode = request.form.get("passcode", "")

    if not all([name, phone_number, email, passcode]):
        flash("Semua field wajib diisi.", "danger")
        return redirect(url_for("auth.login_page"))

    if len(passcode) < 6:
        flash("Passcode minimal 6 karakter.", "danger")
        return redirect(url_for("auth.login_page"))

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        if existing_user.is_email_verified:
            flash(
                "Email sudah terdaftar. Silakan login.",
                "warning"
            )
            return redirect(url_for("auth.login_page"))

        # Pengguna sudah mendaftar, tetapi belum verifikasi.
        # Buat OTP baru.
        otp_code = existing_user.generate_email_verification_otp()

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Gagal menyimpan OTP baru: {e}")

            flash(
                "Gagal membuat kode OTP. Silakan coba kembali.",
                "danger"
            )
            return redirect(url_for("auth.login_page"))

        try:
            send_otp_email(
                to_email=existing_user.email,
                name=existing_user.name,
                otp_code=otp_code,
            )
        except Exception as e:
            print(f"[WARN] Gagal mengirim OTP: {e}")

            flash(
                "Kode OTP gagal dikirim. Silakan coba kirim ulang.",
                "warning"
            )

        session["pending_verification_email"] = existing_user.email

        return redirect(url_for("auth.verify_email_page"))

    new_user = User(
        name=name,
        email=email,
        phone_number=phone_number,
        role="customer",
        is_email_verified=False,
    )

    new_user.set_password(passcode)

    # Membuat OTP dan menyimpan hash OTP ke object User.
    otp_code = new_user.generate_email_verification_otp()

    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Gagal menyimpan pengguna: {e}")

        flash(
            "Pendaftaran gagal. Silakan coba kembali.",
            "danger"
        )
        return redirect(url_for("auth.login_page"))

    session["pending_verification_email"] = new_user.email

    try:
        send_otp_email(
            to_email=new_user.email,
            name=new_user.name,
            otp_code=otp_code,
        )

        flash(
            "Pendaftaran berhasil. Kode OTP telah dikirim ke email Anda.",
            "success"
        )
    except Exception as e:
        print(f"[WARN] Gagal mengirim OTP verifikasi: {e}")

        flash(
            "Akun berhasil dibuat, tetapi OTP gagal dikirim. "
            "Silakan pilih kirim ulang OTP.",
            "warning"
        )

    # Jangan login_user(new_user) di sini.
    return redirect(url_for("auth.verify_email_page"))


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Sesuai mockup Login: Email Address + Passcode.
    """
    email = request.form.get("email", "").strip().lower()
    passcode = request.form.get("passcode", "")

    user = User.query.filter_by(email=email).first()

    if not user:
        flash("Email belum terdaftar.", "danger")
        return redirect(url_for("auth.login_page"))

    if not user.check_password(passcode):
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


# ── Forgot Password ──────────────────────────────────────────
@auth_bp.route("/forgot-password", methods=["GET"])
def forgot_password_page():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard" if current_user.is_admin else "customer.dashboard"))
    return render_template("auth/forgot_password.html")


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    email = request.form.get("email", "").strip().lower()
    user = User.query.filter_by(email=email).first()

    if user:
        token = user.generate_reset_token()
        reset_link = url_for("auth.reset_password_page", token=token, _external=True)
        try:
            kirim_reset_password_email(email_tujuan=user.email, name=user.name, reset_link=reset_link)
        except Exception as e:
            print(f"[WARN] Gagal mengirim email reset passcode: {e}")

    # Pesan sukses selalu sama walau email tidak ditemukan,
    # supaya tidak bisa dipakai untuk mengecek email mana yang terdaftar.
    flash("Jika email terdaftar, link reset passcode sudah dikirim ke email tersebut.", "info")
    return redirect(url_for("auth.login_page"))


# ── Reset Password ───────────────────────────────────────────
@auth_bp.route("/reset-password/<token>", methods=["GET"])
def reset_password_page(token):
    user = User.verify_reset_token(token)
    if not user:
        flash("Link reset passcode tidak valid atau sudah kedaluwarsa.", "danger")
        return redirect(url_for("auth.forgot_password_page"))

    return render_template("auth/reset_password.html", token=token)


@auth_bp.route("/reset-password/<token>", methods=["POST"])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash("Link reset passcode tidak valid atau sudah kedaluwarsa.", "danger")
        return redirect(url_for("auth.forgot_password_page"))

    passcode = request.form.get("passcode", "")
    confirm_passcode = request.form.get("confirm_passcode", "")

    if len(passcode) < 6:
        flash("Passcode minimal 6 karakter.", "danger")
        return redirect(url_for("auth.reset_password_page", token=token))

    if passcode != confirm_passcode:
        flash("Konfirmasi passcode tidak cocok.", "danger")
        return redirect(url_for("auth.reset_password_page", token=token))

    user.set_password(passcode)
    db.session.commit()

    flash("Passcode berhasil diubah. Silakan login dengan passcode baru.", "success")
    return redirect(url_for("auth.login_page"))
