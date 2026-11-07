from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email

from .models import User

auth = Blueprint("auth", __name__)


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(
            email=form.email.data.strip().lower(),
            is_active=True
        ).first()

        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("admin.dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html", form=form)


@auth.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return redirect(url_for("auth.login"))