import os
from flask import Flask

from config import config_by_name
from app.extensions import db, migrate, login_manager, bcrypt, cors
from app.utils.cloudinary_client import init_cloudinary
from app.services.email_service import init_resend


def create_app(config_name=None):
    """
    Application Factory.
    config_name diambil dari env var FLASK_ENV (lewat os.getenv), default "development".
    """
    config_name = config_name or os.getenv("FLASK_ENV", "development")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name[config_name])

    # --- Init ekstensi ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app)

    # --- Init layanan pihak ketiga (baca config yang sumbernya os.getenv) ---
    init_cloudinary(app)
    init_resend(app)

    # --- Import model supaya dikenali Flask-Migrate ---
    from app.models.user import User
    # --- User loader untuk Flask-Login ---
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    # --- Register Blueprints ---
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.customer import customer_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp)

    return app
