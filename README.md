# Next Level Rent

Sistem reservasi room PlayStation. Backend Flask (Application Factory + Blueprints), database **TiDB Cloud Serverless**, email via **Resend**, upload gambar via **Cloudinary**.

## 📁 Struktur Folder

```
next-level-rent/
├── app/
│   ├── __init__.py          # Application Factory
│   ├── extensions.py        # db, migrate, login_manager, bcrypt, cors
│   ├── models/               # User, Room, Reservation, Payment
│   ├── routes/               # Blueprints: main, auth, customer, admin
│   ├── services/             # email_service (Resend), upload_service (Cloudinary)
│   ├── utils/                 # cloudinary_client
│   ├── static/                # css, js, uploads
│   └── templates/             # auth, customer, admin, emails
├── migrations/                # Flask-Migrate (Alembic)
├── instance/                  # config khusus instance (tidak di-commit)
├── config.py                  # Baca semua secret via os.getenv()
├── run.py                     # Entry point development
├── wsgi.py                    # Entry point production (gunicorn)
├── requirements.txt
├── .env.example
└── .gitignore
```

## 🗄️ Skema Database (sesuai Use Case Diagram)

| Tabel | Keterangan |
|---|---|
| `users` | Customer & Admin (dibedakan kolom `role`) |
| `rooms` | Room/unit PS yang disewakan, dipakai di "Choose Available Room" & "Manage Room" |
| `reservations` | Reservasi online (customer) maupun offline (dibuat admin) |
| `payments` | Pembayaran, generalisasi CASH / CASHLESS |

Relasi: `User 1—N Reservation N—1 Room`, `Reservation 1—1 Payment`.

## ⚙️ Setup

### 1. Clone & install dependencies
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Setup TiDB Cloud Serverless
1. Daftar di [tidbcloud.com](https://tidbcloud.com) → buat cluster **Serverless** (gratis).
2. Buka cluster → tab **Connect** → pilih driver **General (SQLAlchemy)** atau **PyMySQL**.
3. Catat: `Host`, `Port` (4000), `User`, `Password`, lalu buat database `next_level_rent`.
4. Download CA cert root yang ditunjukkan di halaman Connect (biasanya tinggal pakai cert sistem `/etc/ssl/cert.pem` di Mac/Linux, atau download `isrgrootx1.pem` untuk Windows).

### 3. Setup Resend
1. Daftar di [resend.com](https://resend.com) → **API Keys** → buat key baru.
2. Verifikasi domain pengirim (atau pakai domain test `onboarding@resend.dev` saat development).

### 4. Setup Cloudinary
1. Daftar di [cloudinary.com](https://cloudinary.com) → buka **Dashboard**.
2. Catat `Cloud Name`, `API Key`, `API Secret`.

### 5. Buat file `.env`
```bash
cp .env.example .env
```
Lalu isi semua value sesuai kredensial dari langkah 2–4. Semua dibaca lewat `os.getenv()` di `config.py`.

### 6. Migrasi database
```bash
flask db init        # hanya sekali, generate folder migrations/
flask db migrate -m "initial schema"
flask db upgrade
```

### 7. Jalankan aplikasi
```bash
python run.py
```
Buka [http://127.0.0.1:5000](http://127.0.0.1:5000) → otomatis redirect ke halaman Login/Sign Up.

## 🔐 Catatan Keamanan
- Passcode disimpan dengan hashing **bcrypt** (`Flask-Bcrypt`), tidak pernah disimpan plain text.
- `.env` sudah masuk `.gitignore`, jangan commit credential ke repo.
- TiDB Cloud Serverless mewajibkan koneksi SSL/TLS.

## 🚀 Production
Gunakan `wsgi.py` dengan Gunicorn:
```bash
gunicorn wsgi:app
```
