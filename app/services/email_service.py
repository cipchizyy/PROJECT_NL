import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(to_email, subject, html_body):
    """
    Fungsi utama untuk mengirim email langsung lewat Gmail SMTP.
    """
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")
    mail_from = os.getenv("MAIL_FROM")

    if not mail_username or not mail_password or not mail_from:
        raise Exception("Konfigurasi MAIL_USERNAME / MAIL_PASSWORD / MAIL_FROM belum lengkap di .env")

    message = MIMEMultipart("alternative")
    message["From"] = mail_from
    message["To"] = to_email
    message["Subject"] = subject

    message.attach(MIMEText(html_body, "html"))

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(mail_username, mail_password)
    server.sendmail(mail_from, to_email, message.as_string())
    server.quit()


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