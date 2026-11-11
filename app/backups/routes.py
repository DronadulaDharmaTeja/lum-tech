
from pathlib import Path

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    send_file,
    abort
)

from flask_login import login_required, current_user

from .service import (
    create_database_backup,
    list_database_backups,
    get_backup_file
)


# =========================================================
# BACKUP BLUEPRINT
# =========================================================

backups = Blueprint(
    "backups",
    __name__,
    url_prefix="/admin/backups"
)


# =========================================================
# SUPER ADMIN SECURITY
# =========================================================

def super_admin_required():

    if not current_user.is_authenticated:
        abort(401)

    if current_user.role != "super_admin":
        abort(403)


# =========================================================
# BACKUP DASHBOARD
# =========================================================

@backups.route("/")
@login_required
def index():

    super_admin_required()

    backup_records = list_database_backups()

    backup_items = []

    for record in backup_records:

        try:
            file_path = get_backup_file(record.filename)

            file_size = file_path.stat().st_size

            file_exists = True

        except (FileNotFoundError, ValueError):

            file_size = 0

            file_exists = False

        backup_items.append({
            "record": record,
            "file_size": file_size,
            "file_exists": file_exists
        })

    return render_template(
        "backups/index.html",
        backups=backup_items
    )


# =========================================================
# CREATE DATABASE BACKUP
# =========================================================

@backups.route("/create", methods=["POST"])
@login_required
def create_backup():

    super_admin_required()

    try:

        backup_record = create_database_backup()

        flash(
            f"Backup created successfully: {backup_record.filename}",
            "success"
        )

    except Exception as error:

        flash(
            f"Backup creation failed: {error}",
            "error"
        )

    return redirect(
        url_for("backups.index")
    )


# =========================================================
# DOWNLOAD DATABASE BACKUP
# =========================================================

@backups.route("/download/<int:backup_id>")
@login_required
def download_backup():

    super_admin_required()

    abort(404)


@backups.route("/download-file/<int:backup_id>")
@login_required
def download_backup_file(backup_id):

    super_admin_required()

    from ..models import BackupRecord

    record = BackupRecord.query.get_or_404(
        backup_id
    )

    try:

        file_path = get_backup_file(
            record.filename
        )

        return send_file(
            file_path,
            as_attachment=True,
            download_name=record.filename,
            mimetype="application/sql"
        )

    except (FileNotFoundError, ValueError):

        flash(
            "The requested backup file could not be found.",
            "error"
        )

        return redirect(
            url_for("backups.index")
        )
