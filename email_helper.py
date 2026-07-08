import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from flask import render_template

load_dotenv()

def kirim_otp_email(email_tujuan, otp):
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        email_pengirim = os.getenv("MAIL_USERNAME")
        password_email = os.getenv("MAIL_PASSWORD")
        email_from = os.getenv("MAIL_FROM")

        if not email_pengirim or not password_email or not email_from:
            print("[ERROR] Konfigurasi email belum lengkap di .env")
            return False

        subject = "Kode OTP Verifikasi Akun"

        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Verifikasi Akun</h2>
                <p>Kode OTP kamu adalah:</p>
                <h1 style="letter-spacing: 5px;">{otp}</h1>
                <p>Jangan berikan kode ini kepada siapa pun.</p>
            </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["From"] = email_from
        message["To"] = email_tujuan
        message["Subject"] = subject
        message.attach(MIMEText(body, "html"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_pengirim, password_email)
        server.sendmail(email_from, email_tujuan, message.as_string())
        server.quit()

        print(f"[INFO] OTP berhasil dikirim ke {email_tujuan}")
        return True

    except Exception as e:
        print(f"[ERROR] Gagal mengirim OTP email: {e}")
        return False


def kirim_reset_password_email(email_tujuan, name, reset_link):
    """
    Kirim email berisi link reset passcode.
    Dipanggil dari app/routes/auth.py (route forgot-password).
    Pakai template Jinja app/templates/emails/password_reset.html
    """
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        email_pengirim = os.getenv("MAIL_USERNAME")
        password_email = os.getenv("MAIL_PASSWORD")
        email_from = os.getenv("MAIL_FROM")

        if not email_pengirim or not password_email or not email_from:
            print("[ERROR] Konfigurasi email belum lengkap di .env")
            return False

        subject = "Reset Passcode Next Level"

        body = render_template(
            "emails/password_reset.html",
            name=name,
            reset_link=reset_link,
        )

        message = MIMEMultipart("alternative")
        message["From"] = email_from
        message["To"] = email_tujuan
        message["Subject"] = subject
        message.attach(MIMEText(body, "html"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_pengirim, password_email)
        server.sendmail(email_from, email_tujuan, message.as_string())
        server.quit()

        print(f"[INFO] Email reset passcode berhasil dikirim ke {email_tujuan}")
        return True

    except Exception as e:
        print(f"[ERROR] Gagal mengirim email reset passcode: {e}")
        return False