import os
from time import perf_counter

from flask import Flask, g, request

from config import config_by_name
from app.extensions import (
    bcrypt,
    cors,
    db,
    login_manager,
    migrate,
)
from app.utils.cloudinary_client import (
    cloudinary_thumbnail_url,
    init_cloudinary,
)


def create_app(config_name=None):
    config_name = config_name or os.getenv("FLASK_ENV", "development")

    if config_name not in config_by_name:
        raise ValueError(f"Konfigurasi '{config_name}' tidak tersedia.")

    is_production = config_name == "production"

    if is_production:
        # Pada Vercel, file public/** dilayani langsung oleh CDN.
        app = Flask(
            __name__,
            instance_relative_config=True,
            static_folder=None,
        )

        # Memungkinkan url_for("static", ...) tetap menghasilkan URL
        # meskipun Flask tidak melayani file static di production.
        app.add_url_rule(
            "/static/<path:filename>",
            endpoint="static",
            build_only=True,
        )
    else:
        # Pada development lokal, Flask melayani public/static.
        app = Flask(
            __name__,
            instance_relative_config=True,
            static_folder="../public/static",
            static_url_path="/static",
        )

    app.config.from_object(config_by_name[config_name])

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app)

    # Cloudinary
    init_cloudinary(app)

    app.jinja_env.filters["cloudinary_thumb"] = cloudinary_thumbnail_url

    # Import model agar dikenali SQLAlchemy dan Flask-Migrate.
    from app.models.user import User
    from app.models.room import Room  # noqa: F401
    from app.models.reservation import Reservation  # noqa: F401
    from app.models.payment import Payment  # noqa: F401
    from app.models.game import Game  # noqa: F401
    from app.models.otp_code import OtpCode  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, user_id)

    # Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.customer import customer_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp)

    # Performance measurement
    @app.before_request
    def start_request_timer():
        g.request_started_at = perf_counter()

    @app.after_request
    def add_server_timing(response):
        started_at = getattr(
            g,
            "request_started_at",
            None,
        )

        if started_at is not None:
            duration_ms = (perf_counter() - started_at) * 1000

            response.headers["Server-Timing"] = f"app;dur={duration_ms:.1f}"

            # Hindari log berulang untuk file static saat development.
            if request.endpoint != "static":
                app.logger.info(
                    "PERF %s %s %.1fms",
                    request.method,
                    request.path,
                    duration_ms,
                )

        return response

    return app
