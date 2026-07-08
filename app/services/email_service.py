import os
import resend
from flask import render_template


def send_email(to_email, subject, html_body):
    """
    Fungsi utama untuk mengirim email lewat Resend API (HTTPS/443).
    Dipakai daripada SMTP Gmail (587) karena banyak jaringan
    (kampus/kantor/ISP tertentu) memblokir port SMTP keluar,
    sedangkan HTTPS hampir selalu terbuka.
    """
    resend_api_key = os.getenv("RESEND_API_KEY")
    resend_from_email = os.getenv("RESEND_FROM_EMAIL")
    resend_from_name = os.getenv("RESEND_FROM_NAME", "Next Level Rent")

    if not resend_api_key or not resend_from_email:
        raise Exception("Konfigurasi RESEND_API_KEY / RESEND_FROM_EMAIL belum lengkap di .env")

    resend.api_key = resend_api_key

    resend.Emails.send({
        "from": f"{resend_from_name} <{resend_from_email}>",
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    })


def send_otp_email(to_email, name, otp_code):
    """
    Kirim kode OTP untuk verifikasi email saat register.
    Dipanggil dari auth.py.
    """
    subject = "Kode OTP Verifikasi Akun"

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Halo, {name}</h2>
            <p>Terima kasih sudah mendaftar.</p>
            <p>Kode OTP verifikasi email kamu adalah:</p>

            <h1 style="letter-spacing: 6px; color: #2563eb;">
                {otp_code}
            </h1>

            <p>Kode ini berlaku selama 10 menit.</p>
            <p>Jangan berikan kode ini kepada siapa pun.</p>
        </body>
    </html>
    """

    send_email(to_email, subject, html_body)


def send_welcome_email(to_email, name):
    """
    Kirim email selamat datang setelah OTP berhasil diverifikasi.
    Dipanggil dari auth.py.
    """
    subject = "Selamat Datang di Next Level"

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Selamat datang, {name}!</h2>
            <p>Email kamu berhasil diverifikasi.</p>
            <p>Sekarang kamu sudah bisa menggunakan akun Next Level.</p>
        </body>
    </html>
    """

    send_email(to_email, subject, html_body)


def send_password_reset_email(to_email, name, reset_link):
    """
    Kirim email berisi link reset passcode.
    Dipanggil dari auth.py (route forgot-password).
    Pakai template Jinja app/templates/emails/password_reset.html
    """
    subject = "Reset Passcode Next Level"

    html_body = render_template(
        "emails/password_reset.html",
        name=name,
        reset_link=reset_link,
    )

    send_email(to_email, subject, html_body)