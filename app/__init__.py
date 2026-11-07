import click

from flask import Flask, redirect, url_for
from flask_login import current_user
from flask_wtf.csrf import CSRFError

from config import Config
from .extensions import db, login_manager, csrf
from .models import User
from .auth import auth
from .admin import admin


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access the admin panel."

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.register_blueprint(auth)
    app.register_blueprint(admin)

    @app.route("/")
    def home():
        if current_user.is_authenticated:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("auth.login"))

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        return "Your session expired. Please refresh the page and try again.", 400

    @app.cli.command("init-db")
    def init_db():
        """Create the database tables."""
        with app.app_context():
            db.create_all()
        click.echo("LUM TEK database tables created.")

    @app.cli.command("create-admin")
    def create_admin():
        """Create the first administrator account."""
        with app.app_context():
            email = click.prompt("Admin email").strip().lower()
            name = click.prompt("Admin name")
            password = click.prompt(
                "Admin password",
                hide_input=True,
                confirmation_prompt=True
            )

            if len(password) < 12:
                raise click.ClickException(
                    "Use a password with at least 12 characters."
                )

            if User.query.filter_by(email=email).first():
                raise click.ClickException("That email already exists.")

            user = User(
                name=name,
                email=email,
                role="admin",
                is_active=True
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            click.echo("Administrator account created.")

    return app