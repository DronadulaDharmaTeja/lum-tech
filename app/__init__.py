
import click

from flask import Flask, redirect, url_for
from flask_login import current_user
from flask_wtf.csrf import CSRFError

from config import Config

from .extensions import db, login_manager, csrf
from .models import User

from .auth import auth
from .admin import admin

# Data Extraction
from .extraction.models import ExtractionJob, ExtractionRecord
from .extraction.routes import extraction

# Database Backup
from .backups.routes import backups


def create_app():

    app = Flask(__name__)

    # -----------------------------------------
    # APPLICATION CONFIGURATION
    # -----------------------------------------

    app.config.from_object(Config)

    # -----------------------------------------
    # INITIALIZE EXTENSIONS
    # -----------------------------------------

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"

    login_manager.login_message = (
        "Please log in to access the admin panel."
    )

    # -----------------------------------------
    # USER SESSION LOADER
    # -----------------------------------------

    @login_manager.user_loader
    def load_user(user_id):

        try:
            user = db.session.get(User, int(user_id))

            if user and user.is_active:
                return user

            return None

        except (ValueError, TypeError):
            return None

    # -----------------------------------------
    # REGISTER BLUEPRINTS
    # -----------------------------------------

    app.register_blueprint(auth)
    app.register_blueprint(admin)

    # Data Extraction
    app.register_blueprint(extraction)

    # Database Backup
    app.register_blueprint(backups)

    # -----------------------------------------
    # HOME ROUTE
    # -----------------------------------------

    @app.route("/")
    def home():

        if current_user.is_authenticated:
            return redirect(url_for("admin.dashboard"))

        return redirect(url_for("auth.login"))

    # -----------------------------------------
    # CSRF ERROR HANDLER
    # -----------------------------------------

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):

        return (
            "Your session expired. Please refresh the page and try again.",
            400
        )

    # -----------------------------------------
    # INITIALIZE DATABASE COMMAND
    # -----------------------------------------

    @app.cli.command("init-db")
    def init_db():

        """Create database tables."""

        with app.app_context():

            from .extraction.models import (
                ExtractionJob,
                ExtractionRecord
            )

            from .models import BackupRecord

            db.create_all()

        click.echo(
            "LUM TEK database tables created successfully."
        )

    # -----------------------------------------
    # CREATE SUPER ADMIN COMMAND
    # -----------------------------------------

    @app.cli.command("create-super-admin")
    def create_super_admin():

        """Create the initial Super Admin account."""

        with app.app_context():

            existing_super_admin = User.query.filter_by(
                role="super_admin"
            ).first()

            if existing_super_admin:

                raise click.ClickException(
                    "A Super Admin account already exists."
                )

            email = click.prompt(
                "Super Admin email"
            ).strip().lower()

            name = click.prompt(
                "Super Admin name"
            ).strip()

            password = click.prompt(
                "Super Admin password",
                hide_input=True,
                confirmation_prompt=True
            )

            if not name or not email:
                raise click.ClickException(
                    "Name and email cannot be empty."
                )

            if len(password) < 12:
                raise click.ClickException(
                    "Password must contain at least 12 characters."
                )

            existing_user = User.query.filter_by(
                email=email
            ).first()

            if existing_user:

                raise click.ClickException(
                    "This email address already exists."
                )

            user = User(
                name=name,
                email=email,
                role="super_admin",
                department=None,
                permissions={},
                is_active=True
            )

            user.set_password(password)

            db.session.add(user)

            try:

                db.session.commit()

            except Exception:

                db.session.rollback()

                raise click.ClickException(
                    "Unable to create Super Admin. Check the database."
                )

            click.echo(
                "Super Admin account created successfully."
            )

    # -----------------------------------------
    # RETURN APPLICATION
    # -----------------------------------------

    return app
