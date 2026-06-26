import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

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