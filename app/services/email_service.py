import os
import smtplib
import ssl

from email.message import EmailMessage
from email.utils import formataddr

from flask import render_template


def send_email(to_email: str, subject: str, html_body: str):
    """
    Fungsi utama untuk mengirim email menggunakan SMTP Gmail.

    Konfigurasi diambil dari file .env:
    - MAIL_HOST
    - MAIL_PORT
    - MAIL_USERNAME
    - MAIL_PASSWORD
    - MAIL_ENCRYPTION
    - MAIL_FROM_ADDRESS
    - MAIL_FROM_NAME
    """

    mail_host = os.getenv("MAIL_HOST", "smtp.gmail.com")
    mail_port = int(os.getenv("MAIL_PORT", "587"))

    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")

    mail_encryption = os.getenv(
        "MAIL_ENCRYPTION",
        "tls"
    ).strip().lower()

    mail_from_address = os.getenv(
        "MAIL_FROM_ADDRESS",
        mail_username
    )

    mail_from_name = os.getenv(
        "MAIL_FROM_NAME",
        "NextLevel Rent PS"
    )

    if not mail_username:
        raise RuntimeError(
            "MAIL_USERNAME belum diatur di file .env."
        )

    if not mail_password:
        raise RuntimeError(
            "MAIL_PASSWORD belum diatur di file .env."
        )

    if not mail_from_address:
        raise RuntimeError(
            "MAIL_FROM_ADDRESS belum diatur di file .env."
        )

    # Google App Password kadang ditampilkan dengan spasi.
    # SMTP Gmail membutuhkan versi tanpa spasi.
    mail_password = mail_password.replace(" ", "")

    message = EmailMessage()

    message["Subject"] = subject
    message["From"] = formataddr(
        (mail_from_name, mail_from_address)
    )
    message["To"] = to_email

    # Versi teks biasa sebagai fallback.
    message.set_content(
        "Email ini menggunakan format HTML. "
        "Silakan buka menggunakan aplikasi email yang mendukung HTML."
    )

    # Versi HTML.
    message.add_alternative(
        html_body,
        subtype="html"
    )

    ssl_context = ssl.create_default_context()

    try:
        if mail_encryption == "ssl" or mail_port == 465:
            # Digunakan untuk SMTP SSL, biasanya port 465.
            with smtplib.SMTP_SSL(
                mail_host,
                mail_port,
                context=ssl_context,
                timeout=12
            ) as smtp:
                smtp.login(
                    mail_username,
                    mail_password
                )
                smtp.send_message(message)

        else:
            # Digunakan untuk STARTTLS, biasanya port 587.
            with smtplib.SMTP(
                mail_host,
                mail_port,
                timeout=12
            ) as smtp:
                smtp.ehlo()

                if mail_encryption == "tls":
                    smtp.starttls(
                        context=ssl_context
                    )
                    smtp.ehlo()

                smtp.login(
                    mail_username,
                    mail_password
                )

                smtp.send_message(message)

    except smtplib.SMTPAuthenticationError as error:
        raise RuntimeError(
            "Login SMTP Gmail gagal. "
            "Pastikan MAIL_PASSWORD menggunakan Google App Password, "
            "bukan password Gmail biasa."
        ) from error

    except smtplib.SMTPException as error:
        raise RuntimeError(
            f"Gagal mengirim email melalui SMTP Gmail: {error}"
        ) from error

    except OSError as error:
        raise RuntimeError(
            f"Tidak dapat terhubung ke server SMTP Gmail: {error}"
        ) from error


def send_otp_email(
    to_email: str,
    name: str,
    otp_code: str
):
    """
    Mengirim OTP verifikasi email setelah customer mendaftar.
    OTP berlaku selama 10 menit.
    """

    subject = "Kode OTP Verifikasi Akun NextLevel Rent PS"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="id">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">
        </head>

        <body style="
            margin: 0;
            padding: 30px;
            background-color: #f3f4f6;
            font-family: Arial, sans-serif;
            color: #111827;
        ">
            <div style="
                max-width: 520px;
                margin: 0 auto;
                padding: 32px;
                background-color: #ffffff;
                border-radius: 12px;
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
            ">
                <h2 style="
                    margin-top: 0;
                    color: #172554;
                ">
                    Verifikasi Email
                </h2>

                <p>Halo, <strong>{name}</strong>.</p>

                <p>
                    Terima kasih telah mendaftar di
                    <strong>NextLevel Rent PS</strong>.
                </p>

                <p>
                    Masukkan kode OTP berikut pada halaman
                    verifikasi:
                </p>

                <div style="
                    margin: 28px 0;
                    padding: 20px;
                    background-color: #eff6ff;
                    border: 1px solid #bfdbfe;
                    border-radius: 10px;
                    text-align: center;
                ">
                    <span style="
                        font-size: 34px;
                        font-weight: bold;
                        letter-spacing: 8px;
                        color: #1d4ed8;
                    ">
                        {otp_code}
                    </span>
                </div>

                <p>
                    Kode OTP berlaku selama
                    <strong>10 menit</strong>.
                </p>

                <p style="color: #dc2626;">
                    Jangan memberikan kode OTP ini kepada siapa pun.
                </p>

                <p style="
                    margin-bottom: 0;
                    color: #6b7280;
                    font-size: 14px;
                ">
                    Abaikan email ini apabila kamu tidak merasa
                    melakukan pendaftaran.
                </p>
            </div>
        </body>
    </html>
    """

    send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body
    )


def send_welcome_email(
    to_email: str,
    name: str
):
    """
    Mengirim email selamat datang setelah OTP berhasil diverifikasi.
    """

    subject = "Selamat Datang di NextLevel Rent PS"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="id">
        <head>
            <meta charset="UTF-8">
        </head>

        <body style="
            margin: 0;
            padding: 30px;
            background-color: #f3f4f6;
            font-family: Arial, sans-serif;
            color: #111827;
        ">
            <div style="
                max-width: 520px;
                margin: 0 auto;
                padding: 32px;
                background-color: #ffffff;
                border-radius: 12px;
            ">
                <h2 style="color: #172554;">
                    Selamat Datang, {name}!
                </h2>

                <p>
                    Email kamu telah berhasil diverifikasi.
                </p>

                <p>
                    Sekarang kamu sudah dapat login dan melakukan
                    reservasi room PlayStation melalui
                    NextLevel Rent PS.
                </p>
            </div>
        </body>
    </html>
    """

    send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body
    )


def send_password_reset_email(
    to_email: str,
    name: str,
    reset_link: str
):
    """
    Mengirim email berisi link untuk reset passcode.
    """

    subject = "Reset Passcode NextLevel Rent PS"

    html_body = render_template(
        "emails/password_reset.html",
        name=name,
        reset_link=reset_link,
    )

    send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body
    )