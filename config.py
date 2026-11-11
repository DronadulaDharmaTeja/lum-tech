
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL


# ============================================================
# PROJECT DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from backend/.env
load_dotenv(BASE_DIR / ".env")


# ============================================================
# FLASK CONFIGURATION
# ============================================================

class Config:

    # --------------------------------------------------------
    # APPLICATION SECURITY
    # --------------------------------------------------------

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "change-this-secret-key-before-deployment"
    )

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    SESSION_COOKIE_SECURE = (
        os.getenv("SESSION_COOKIE_SECURE", "false").lower()
        == "true"
    )

    # --------------------------------------------------------
    # MYSQL DATABASE CONFIGURATION
    # --------------------------------------------------------

    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "lum_tek_db")

    # SQLAlchemy URL.create() safely handles passwords
    # containing @, :, /, # and other special characters.

    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername="mysql+pymysql",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        query={"charset": "utf8mb4"},
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_timeout": 30,
    }

    # --------------------------------------------------------
    # FILE UPLOAD CONFIGURATION
    # --------------------------------------------------------

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    UPLOAD_FOLDER = BASE_DIR / "instance" / "uploads"

    # --------------------------------------------------------
    # DATABASE BACKUP CONFIGURATION
    # --------------------------------------------------------

    BACKUP_FOLDER = (
        BASE_DIR / "instance" / "database_backups"
    )

    MYSQLDUMP_PATH = os.getenv(
        "MYSQLDUMP_PATH",
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"
    )

    BACKUP_TIMEOUT = 600

    # --------------------------------------------------------
    # DATABASE RESTORE CONFIGURATION
    # --------------------------------------------------------

    MYSQL_PATH = os.getenv(
        "MYSQL_PATH",
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
    )

    RESTORE_TIMEOUT = 600

    # --------------------------------------------------------
    # CSRF PROTECTION
    # --------------------------------------------------------

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # --------------------------------------------------------
    # JSON CONFIGURATION
    # --------------------------------------------------------

    JSON_SORT_KEYS = False

    # --------------------------------------------------------
    # DEBUG CONFIGURATION
    # --------------------------------------------------------

    DEBUG = (
        os.getenv("FLASK_DEBUG", "false").lower()
        == "true"
    )
