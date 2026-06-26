import resend
from flask import current_app, render_template


def init_resend(app):
    """Set API key Resend dari .env (lewat app.config yang sumbernya os.getenv)."""
    resend.api_key = app.config["RESEND_API_KEY"]


def _from_address():
    name = current_app.config["RESEND_FROM_NAME"]
    email = current_app.config["RESEND_FROM_EMAIL"]
    return f"{name} <{email}>"


def send_welcome_email(to_email: str, name: str):
    """Dikirim setelah Sign Up berhasil."""
    params = {
        "from": _from_address(),
        "to": [to_email],
        "subject": "Selamat Bergabung di Next Level Rent!",
        "html": render_template("emails/welcome.html", name=name),
    }
    return resend.Emails.send(params)


def send_otp_email(to_email: str, name: str, otp_code: str):
    """Dikirim saat Sign Up, untuk verifikasi email lewat kode OTP 6 digit."""
    params = {
        "from": _from_address(),
        "to": [to_email],
        "subject": f"{otp_code} adalah kode verifikasi Next Level Rent kamu",
        "html": render_template("emails/otp_verification.html", name=name, otp_code=otp_code),
    }
    return resend.Emails.send(params)


def send_reservation_confirmation_email(to_email: str, name: str, reservation):
    """Dikirim setelah Make Room Reservation berhasil & payment dibuat."""
    params = {
        "from": _from_address(),
        "to": [to_email],
        "subject": "Konfirmasi Reservasi - Next Level Rent",
        "html": render_template(
            "emails/reservation_confirmation.html",
            name=name,
            reservation=reservation,
        ),
    }
    return resend.Emails.send(params)


def send_password_reset_email(to_email: str, name: str, reset_link: str):
    """Opsional: kalau nanti butuh fitur reset password."""
    params = {
        "from": _from_address(),
        "to": [to_email],
        "subject": "Reset Passcode - Next Level Rent",
        "html": render_template(
            "emails/password_reset.html",
            name=name,
            reset_link=reset_link,
        ),
    }
    return resend.Emails.send(params)