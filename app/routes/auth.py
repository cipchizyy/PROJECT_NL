from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models.user import User
from app.models.otp_code import OtpCode
from app.services.email_service import (
    send_otp_email,
    send_welcome_email,
    send_password_reset_email,
)


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

OTP_PURPOSE = "email_verification"
OTP_VALID_MINUTES = 10


@auth_bp.route("/", methods=["GET"])
def login_page():
    """
    Halaman gabungan Login dan Sign Up.
    Jika pengguna sudah login, arahkan ke dashboard sesuai role.
    """
    if current_user.is_authenticated:
        endpoint = (
            "admin.dashboard"
            if current_user.is_admin
            else "customer.dashboard"
        )
        return redirect(url_for(endpoint))

    return render_template("auth/login.html")


@auth_bp.route("/signup", methods=["POST"])
def signup():
    """
    Membuat akun customer baru, membuat OTP, lalu mengarahkan
    pengguna ke halaman verifikasi email.
    """
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
                "Email sudah terdaftar dan telah diverifikasi. Silakan login.",
                "warning",
            )
            return redirect(url_for("auth.login_page"))

        try:
            otp = OtpCode.create_for_user(
                user_id=existing_user.id,
                email=existing_user.email,
                purpose=OTP_PURPOSE,
                valid_minutes=OTP_VALID_MINUTES,
            )
        except Exception as error:
            db.session.rollback()
            print(f"[ERROR] Gagal membuat OTP baru: {error}")
            flash("Gagal membuat kode OTP. Silakan coba kembali.", "danger")
            return redirect(url_for("auth.login_page"))

        session["pending_verification_email"] = existing_user.email

        try:
            send_otp_email(
                to_email=existing_user.email,
                name=existing_user.name,
                otp_code=otp.code,
            )
            flash(
                "Akun belum diverifikasi. Kode OTP baru telah dikirim.",
                "info",
            )
        except Exception as error:
            print(f"[WARN] Gagal mengirim OTP: {error}")
            flash(
                "Kode OTP berhasil dibuat, tetapi email gagal dikirim. "
                "Silakan gunakan tombol kirim ulang.",
                "warning",
            )

        return redirect(url_for("auth.verify_otp_page"))

    new_user = User(
        name=name,
        email=email,
        phone_number=phone_number,
        role="customer",
        is_email_verified=False,
    )
    new_user.set_password(passcode)

    try:
        db.session.add(new_user)
        db.session.flush()

        otp = OtpCode.create_for_user(
            user_id=new_user.id,
            email=new_user.email,
            purpose=OTP_PURPOSE,
            valid_minutes=OTP_VALID_MINUTES,
        )
    except Exception as error:
        db.session.rollback()
        print(f"[ERROR] Gagal menyimpan pengguna dan OTP: {error}")
        flash("Pendaftaran gagal. Silakan coba kembali.", "danger")
        return redirect(url_for("auth.login_page"))

    session["pending_verification_email"] = new_user.email

    try:
        send_otp_email(
            to_email=new_user.email,
            name=new_user.name,
            otp_code=otp.code,
        )
        flash(
            "Pendaftaran berhasil. Kode OTP telah dikirim ke email Anda.",
            "success",
        )
    except Exception as error:
        print(f"[WARN] Gagal mengirim OTP verifikasi: {error}")
        flash(
            "Akun berhasil dibuat, tetapi email OTP gagal dikirim. "
            "Silakan gunakan tombol kirim ulang.",
            "warning",
        )

    return redirect(url_for("auth.verify_otp_page"))


@auth_bp.route("/verify-otp", methods=["GET"])
def verify_otp_page():
    """
    Menampilkan halaman input OTP untuk email yang sedang diverifikasi.
    """
    if current_user.is_authenticated:
        endpoint = (
            "admin.dashboard"
            if current_user.is_admin
            else "customer.dashboard"
        )
        return redirect(url_for(endpoint))

    email = session.get("pending_verification_email")

    if not email:
        flash(
            "Sesi verifikasi tidak ditemukan. Silakan daftar atau login kembali.",
            "warning",
        )
        return redirect(url_for("auth.login_page"))

    user = User.query.filter_by(email=email).first()

    if not user:
        session.pop("pending_verification_email", None)
        flash("Akun tidak ditemukan.", "danger")
        return redirect(url_for("auth.login_page"))

    if user.is_email_verified:
        session.pop("pending_verification_email", None)
        flash("Email sudah diverifikasi. Silakan login.", "info")
        return redirect(url_for("auth.login_page"))

    return render_template("emails/verify_otp.html", email=email)


@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    """
    Memeriksa OTP terbaru yang belum digunakan dan menandai email
    sebagai terverifikasi jika kode benar.
    """
    email = session.get("pending_verification_email")

    if not email:
        flash(
            "Sesi verifikasi sudah berakhir. Silakan daftar atau login kembali.",
            "danger",
        )
        return redirect(url_for("auth.login_page"))

    # Mendukung input satu field bernama "otp" maupun enam field digit1-digit6.
    otp_code = request.form.get("otp", "").strip()

    if not otp_code:
        otp_code = "".join(
            request.form.get(f"digit{number}", "").strip()
            for number in range(1, 7)
        )

    if len(otp_code) != 6 or not otp_code.isdigit():
        flash("Kode OTP harus terdiri dari 6 angka.", "danger")
        return redirect(url_for("auth.verify_otp_page"))

    user = User.query.filter_by(email=email).first()

    if not user:
        session.pop("pending_verification_email", None)
        flash("Akun tidak ditemukan.", "danger")
        return redirect(url_for("auth.login_page"))

    if user.is_email_verified:
        session.pop("pending_verification_email", None)
        flash("Email sudah diverifikasi. Silakan login.", "info")
        return redirect(url_for("auth.login_page"))

    otp = (
        OtpCode.query.filter_by(
            user_id=user.id,
            purpose=OTP_PURPOSE,
            is_used=False,
        )
        .order_by(OtpCode.created_at.desc())
        .first()
    )

    if not otp:
        flash(
            "Kode OTP tidak ditemukan. Silakan kirim ulang kode.",
            "danger",
        )
        return redirect(url_for("auth.verify_otp_page"))

    if otp.is_expired:
        try:
            otp.is_used = True
            db.session.commit()
        except Exception as error:
            db.session.rollback()
            print(f"[ERROR] Gagal menandai OTP kedaluwarsa: {error}")

        flash(
            "Kode OTP sudah kedaluwarsa. Silakan kirim ulang kode.",
            "danger",
        )
        return redirect(url_for("auth.verify_otp_page"))

    if not otp.is_valid(otp_code):
        flash("Kode OTP yang dimasukkan salah.", "danger")
        return redirect(url_for("auth.verify_otp_page"))

    try:
        otp.is_used = True
        user.is_email_verified = True
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        print(f"[ERROR] Gagal menyimpan verifikasi email: {error}")
        flash("Verifikasi gagal disimpan. Silakan coba kembali.", "danger")
        return redirect(url_for("auth.verify_otp_page"))

    session.pop("pending_verification_email", None)

    try:
        send_welcome_email(
            to_email=user.email,
            name=user.name,
        )
    except Exception as error:
        # Verifikasi tetap berhasil meskipun welcome email gagal dikirim.
        print(f"[WARN] Gagal mengirim welcome email: {error}")

    flash("Email berhasil diverifikasi. Silakan login.", "success")
    return redirect(url_for("auth.login_page"))


@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    """
    Membuat OTP baru dan mengirimkannya kembali ke email pengguna.
    """
    email = session.get("pending_verification_email")

    if not email:
        flash(
            "Sesi verifikasi tidak ditemukan. Silakan login kembali.",
            "danger",
        )
        return redirect(url_for("auth.login_page"))

    user = User.query.filter_by(email=email).first()

    if not user:
        session.pop("pending_verification_email", None)
        flash("Akun tidak ditemukan.", "danger")
        return redirect(url_for("auth.login_page"))

    if user.is_email_verified:
        session.pop("pending_verification_email", None)
        flash("Email sudah diverifikasi. Silakan login.", "info")
        return redirect(url_for("auth.login_page"))

    try:
        otp = OtpCode.create_for_user(
            user_id=user.id,
            email=user.email,
            purpose=OTP_PURPOSE,
            valid_minutes=OTP_VALID_MINUTES,
        )
    except Exception as error:
        db.session.rollback()
        print(f"[ERROR] Gagal membuat ulang OTP: {error}")
        flash("Gagal membuat kode OTP baru.", "danger")
        return redirect(url_for("auth.verify_otp_page"))

    try:
        send_otp_email(
            to_email=user.email,
            name=user.name,
            otp_code=otp.code,
        )
        flash("Kode OTP baru telah dikirim ke email Anda.", "success")
    except Exception as error:
        print(f"[WARN] Gagal mengirim ulang OTP: {error}")
        flash(
            "Kode OTP berhasil dibuat, tetapi email gagal dikirim.",
            "danger",
        )

    return redirect(url_for("auth.verify_otp_page"))


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login menggunakan email dan passcode.
    Customer yang belum verifikasi email tidak boleh masuk dashboard.
    """
    email = request.form.get("email", "").strip().lower()
    passcode = request.form.get("passcode", "")

    if not email or not passcode:
        flash("Email dan passcode wajib diisi.", "danger")
        return redirect(url_for("auth.login_page"))

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

    if not user.is_admin and not user.is_email_verified:
        session["pending_verification_email"] = user.email
        flash(
            "Email belum diverifikasi. Silakan masukkan kode OTP.",
            "warning",
        )
        return redirect(url_for("auth.verify_otp_page"))

    login_user(user)
    session.pop("pending_verification_email", None)

    flash(f"Selamat datang kembali, {user.name}!", "success")

    if user.is_admin:
        return redirect(url_for("admin.dashboard"))

    return redirect(url_for("customer.dashboard"))


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.pop("pending_verification_email", None)
    flash("Anda telah logout.", "info")
    return redirect(url_for("auth.login_page"))


# ── Forgot Password ──────────────────────────────────────────
@auth_bp.route("/forgot-password", methods=["GET"])
def forgot_password_page():
    if current_user.is_authenticated:
        endpoint = (
            "admin.dashboard"
            if current_user.is_admin
            else "customer.dashboard"
        )
        return redirect(url_for(endpoint))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    email = request.form.get("email", "").strip().lower()
    user = User.query.filter_by(email=email).first()

    if user:
        token = user.generate_reset_token()
        reset_link = url_for(
            "auth.reset_password_page",
            token=token,
            _external=True,
        )

        try:
            send_password_reset_email(
                to_email=user.email,
                name=user.name,
                reset_link=reset_link,
            )
        except Exception as error:
            print(f"[WARN] Gagal mengirim email reset passcode: {error}")

    # Pesan sengaja dibuat sama, baik email ditemukan maupun tidak.
    flash(
        "Jika email terdaftar, link reset passcode sudah dikirim ke email tersebut.",
        "info",
    )
    return redirect(url_for("auth.login_page"))


# ── Reset Password ───────────────────────────────────────────
@auth_bp.route("/reset-password/<token>", methods=["GET"])
def reset_password_page(token):
    user = User.verify_reset_token(token)

    if not user:
        flash(
            "Link reset passcode tidak valid atau sudah kedaluwarsa.",
            "danger",
        )
        return redirect(url_for("auth.forgot_password_page"))

    return render_template("auth/reset_password.html", token=token)


@auth_bp.route("/reset-password/<token>", methods=["POST"])
def reset_password(token):
    user = User.verify_reset_token(token)

    if not user:
        flash(
            "Link reset passcode tidak valid atau sudah kedaluwarsa.",
            "danger",
        )
        return redirect(url_for("auth.forgot_password_page"))

    passcode = request.form.get("passcode", "")
    confirm_passcode = request.form.get("confirm_passcode", "")

    if len(passcode) < 6:
        flash("Passcode minimal 6 karakter.", "danger")
        return redirect(url_for("auth.reset_password_page", token=token))

    if passcode != confirm_passcode:
        flash("Konfirmasi passcode tidak cocok.", "danger")
        return redirect(url_for("auth.reset_password_page", token=token))

    try:
        user.set_password(passcode)
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        print(f"[ERROR] Gagal menyimpan passcode baru: {error}")
        flash("Passcode gagal diubah. Silakan coba kembali.", "danger")
        return redirect(url_for("auth.reset_password_page", token=token))

    flash(
        "Passcode berhasil diubah. Silakan login dengan passcode baru.",
        "success",
    )
    return redirect(url_for("auth.login_page"))
