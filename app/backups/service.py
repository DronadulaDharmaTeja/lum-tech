
import os
import shutil
import subprocess

from datetime import datetime
from pathlib import Path

from flask import current_app
from sqlalchemy.engine import make_url

from ..extensions import db
from ..models import BackupRecord


def get_backup_directory():
    """Return the private backup storage directory."""

    backup_folder = Path(
        current_app.config["BACKUP_FOLDER"]
    )

    backup_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    return backup_folder


def get_mysqldump_executable():
    """Find the MySQL mysqldump executable."""

    configured_path = current_app.config.get(
        "MYSQLDUMP_PATH"
    )

    if configured_path:
        executable = Path(configured_path)

        if executable.is_file():
            return str(executable)

        raise FileNotFoundError(
            "Configured MYSQLDUMP_PATH does not exist."
        )

    executable = shutil.which("mysqldump")

    if executable:
        return executable

    raise FileNotFoundError(
        "mysqldump was not found. Install MySQL Server "
        "or configure MYSQLDUMP_PATH in config.py."
    )


def get_database_connection_details():
    """Read database connection details from SQLAlchemy."""

    database_url = make_url(
        current_app.config["SQLALCHEMY_DATABASE_URI"]
    )

    if database_url.get_backend_name() != "mysql":
        raise ValueError(
            "This backup service currently supports MySQL only."
        )

    if not database_url.username:
        raise ValueError(
            "MySQL database username is not configured."
        )

    if not database_url.database:
        raise ValueError(
            "MySQL database name is not configured."
        )

    return database_url


def create_database_backup():
    """
    Create a MySQL SQL backup.

    Returns the BackupRecord after a successful backup.
    """

    backup_directory = get_backup_directory()

    mysqldump = get_mysqldump_executable()

    database_url = get_database_connection_details()

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = f"lum_tek_backup_{timestamp}.sql"

    final_path = backup_directory / filename

    temporary_path = backup_directory / (
        filename + ".partial"
    )

    command = [
        mysqldump,
        "--single-transaction",
        "--routines",
        "--triggers",
        "--events",
        "--hex-blob",
        "--default-character-set=utf8mb4",
        "--host=" + str(database_url.host or "localhost"),
        "--port=" + str(database_url.port or 3306),
        "--user=" + str(database_url.username),
        str(database_url.database)
    ]

    environment = os.environ.copy()

    if database_url.password:
        environment["MYSQL_PWD"] = database_url.password

    try:

        with open(
            temporary_path,
            "wb"
        ) as backup_file:

            result = subprocess.run(
                command,
                stdout=backup_file,
                stderr=subprocess.PIPE,
                env=environment,
                timeout=600,
                check=False
            )

        if result.returncode != 0:

            error_message = result.stderr.decode(
                "utf-8",
                errors="replace"
            )

            raise RuntimeError(
                "MySQL backup failed: " + error_message
            )

        if (
            not temporary_path.exists()
            or temporary_path.stat().st_size == 0
        ):
            raise RuntimeError(
                "The generated backup file is empty."
            )

        with open(
            temporary_path,
            "rb"
        ) as backup_file:

            beginning = backup_file.read(4096)

        if b"CREATE TABLE" not in beginning and b"CREATE DATABASE" not in beginning:
            # A valid dump may not contain these statements
            # in its first 4096 bytes, so inspect the whole file.
            content = temporary_path.read_bytes()

            if b"CREATE TABLE" not in content:
                raise RuntimeError(
                    "The generated file does not appear to be a valid SQL dump."
                )

        temporary_path.replace(final_path)

        backup_record = BackupRecord(
            filename=filename,
            created_at=datetime.utcnow()
        )

        db.session.add(backup_record)
        db.session.commit()

        return backup_record

    except Exception:

        db.session.rollback()

        if temporary_path.exists():
            temporary_path.unlink()

        if final_path.exists():
            final_path.unlink()

        raise


def list_database_backups():
    """Return backup records, newest first."""

    return BackupRecord.query.order_by(
        BackupRecord.created_at.desc()
    ).all()


def get_backup_file(filename):
    """Resolve a backup filename safely."""

    if (
        not filename
        or Path(filename).name != filename
        or not filename.endswith(".sql")
    ):
        raise ValueError(
            "Invalid backup filename."
        )

    backup_path = (
        get_backup_directory() / filename
    ).resolve()

    backup_directory = get_backup_directory().resolve()

    if backup_path.parent != backup_directory:
        raise ValueError(
            "Invalid backup file location."
        )

    if not backup_path.is_file():
        raise FileNotFoundError(
            "Backup file was not found."
        )

    return backup_path
