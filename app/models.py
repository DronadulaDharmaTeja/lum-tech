
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db


# =========================================================
# 1. USERS
# =========================================================

class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    # Account access levels:
    # super_admin, admin, staff

    role = db.Column(
        db.String(30),
        nullable=False,
        default="staff"
    )

    # LUM TEK business department

    department = db.Column(
        db.String(80),
        nullable=True
    )

    # LUM TEK employee job title

    job_title = db.Column(
        db.String(100),
        nullable=True
    )

    # Individual module permissions stored as JSON.
    #
    # Example:
    # {
    #     "projects": ["view", "edit"],
    #     "leads": ["view", "create"]
    # }

    permissions = db.Column(
        db.JSON,
        nullable=False,
        default=dict
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # Set employee password

    def set_password(self, password):

        self.password_hash = generate_password_hash(
            password
        )

    # Verify employee password

    def check_password(self, password):

        return check_password_hash(
            self.password_hash,
            password
        )

    # Check individual module permissions

    def has_permission(self, module, action="view"):

        # Super Admin has complete access.

        if self.role == "super_admin":
            return True

        permissions = self.permissions or {}

        return action in permissions.get(module, [])


# =========================================================
# 2. ADMIN USERS
# Existing model retained for compatibility.
# =========================================================

class AdminUser(db.Model):

    __tablename__ = "admin_users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime
    )

    def set_password(self, password):

        self.password_hash = generate_password_hash(
            password
        )

    def check_password(self, password):

        return check_password_hash(
            self.password_hash,
            password
        )


# =========================================================
# 3. PROJECTS
# =========================================================

class Project(db.Model):

    __tablename__ = "projects"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    location = db.Column(
        db.String(200)
    )

    status = db.Column(
        db.String(30)
    )

    image_url = db.Column(
        db.String(500)
    )

    created_at = db.Column(
        db.DateTime
    )

    category = db.Column(
        db.String(100)
    )

    image = db.Column(
        db.String(255)
    )


# =========================================================
# 4. SERVICES
# =========================================================

class Service(db.Model):

    __tablename__ = "services"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    image = db.Column(
        db.String(255)
    )

    created_at = db.Column(
        db.DateTime
    )

    is_published = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )


# =========================================================
# 5. TESTIMONIALS
# =========================================================

class Testimonial(db.Model):

    __tablename__ = "testimonials"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    customer_name = db.Column(
        db.String(150),
        nullable=False
    )

    review = db.Column(
        db.Text,
        nullable=False
    )

    rating = db.Column(
        db.Integer,
        default=5
    )

    is_approved = db.Column(
        db.Boolean,
        default=False
    )

    is_featured = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime
    )


# =========================================================
# 6. LEADS / QUOTE REQUESTS
# =========================================================

class Lead(db.Model):

    __tablename__ = "leads"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(150)
    )

    phone = db.Column(
        db.String(40)
    )

    service = db.Column(
        db.String(150)
    )

    message = db.Column(
        db.Text
    )

    status = db.Column(
        db.String(30)
    )

    created_at = db.Column(
        db.DateTime
    )


# =========================================================
# 7. CUSTOMERS
# =========================================================

class Customer(db.Model):

    __tablename__ = "customers"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    full_name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(150)
    )

    phone = db.Column(
        db.String(40)
    )

    company = db.Column(
        db.String(150)
    )

    address = db.Column(
        db.Text
    )

    notes = db.Column(
        db.Text
    )

    status = db.Column(
        db.String(30),
        default="active"
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )


# =========================================================
# 8. MEDIA LIBRARY
# =========================================================

class Media(db.Model):

    __tablename__ = "media"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    original_name = db.Column(
        db.String(255)
    )

    file_type = db.Column(
        db.String(80)
    )

    uploaded_at = db.Column(
        db.DateTime
    )


# =========================================================
# 9. PROJECT PROGRESS UPDATES
# =========================================================

class ProgressUpdate(db.Model):

    __tablename__ = "progress_updates"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id"),
        nullable=False
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    image = db.Column(
        db.String(255)
    )

    created_at = db.Column(
        db.DateTime
    )

    project = db.relationship(
        "Project",
        backref=db.backref(
            "progress_updates",
            lazy=True
        )
    )


# =========================================================
# 10. CONTACT MESSAGES
# =========================================================

class ContactMessage(db.Model):

    __tablename__ = "contact_messages"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(150)
    )

    phone = db.Column(
        db.String(40)
    )

    subject = db.Column(
        db.String(200)
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    category = db.Column(
        db.String(50)
    )

    status = db.Column(
        db.String(30)
    )

    created_at = db.Column(
        db.DateTime
    )


# =========================================================
# 11. ENQUIRIES
# =========================================================

class Enquiry(db.Model):

    __tablename__ = "enquiries"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    full_name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        nullable=False
    )

    phone = db.Column(
        db.String(30)
    )

    service = db.Column(
        db.String(150)
    )

    message = db.Column(
        db.Text
    )

    status = db.Column(
        db.String(50),
        default="Pending"
    )

    created_at = db.Column(
        db.DateTime
    )


# =========================================================
# 12. CAREER APPLICATIONS
# =========================================================

class CareerApplication(db.Model):

    __tablename__ = "career_applications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    full_name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        nullable=False
    )

    phone = db.Column(
        db.String(30)
    )

    position = db.Column(
        db.String(150)
    )

    resume_url = db.Column(
        db.String(500)
    )

    cover_letter = db.Column(
        db.Text
    )

    status = db.Column(
        db.String(50),
        default="Pending"
    )

    created_at = db.Column(
        db.DateTime
    )


# =========================================================
# 13. SEO SETTINGS
# =========================================================

class SEOSetting(db.Model):

    __tablename__ = "seo_settings"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    page = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    meta_title = db.Column(
        db.String(255)
    )

    meta_description = db.Column(
        db.Text
    )

    keywords = db.Column(
        db.Text
    )


# =========================================================
# 14. BACKUP RECORDS
# =========================================================

class BackupRecord(db.Model):

    __tablename__ = "backup_records"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime
    )
