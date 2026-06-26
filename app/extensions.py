from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS

# Semua ekstensi diinisialisasi di sini tanpa "app" dulu,
# nanti di-attach ke app lewat .init_app(app) di app/__init__.py
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()
cors = CORS()

# Konfigurasi default LoginManager
login_manager.login_view = "auth.login_page"
login_manager.login_message = "Silakan login dulu untuk mengakses halaman ini."
login_manager.login_message_category = "warning"
