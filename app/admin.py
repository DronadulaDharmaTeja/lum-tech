from functools import wraps
import json

from flask import (
    Blueprint,
    abort,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from flask_login import login_required, current_user

from .extensions import db
from .models import (
    User,
    Project,
    Service,
    Testimonial,
    Lead,
    Media,
    ContactMessage,
    SEOSetting,
)


admin = Blueprint("admin", __name__, url_prefix="/admin")


# =========================================================
# DEPARTMENTS AND JOB TITLES
# =========================================================

DEPARTMENTS = {
    "Project Management": [
        "Project Manager",
        "Assistant Project Manager",
        "Site Coordinator",
        "Planning Engineer",
    ],
    "Construction & Site Operations": [
        "Site Engineer",
        "Site Supervisor",
        "Construction Manager",
        "Quantity Surveyor",
        "Civil Engineer",
    ],
    "Engineering & Technical": [
        "Design Engineer",
        "Technical Engineer",
        "Project Engineer",
        "CAD Engineer",
    ],
    "CCTV & Security Systems": [
        "CCTV Technician",
        "Security Systems Engineer",
        "CCTV Installation Engineer",
        "Security Supervisor",
    ],
    "Electrical & Networking": [
        "Electrical Engineer",
        "Network Engineer",
        "Electrician",
        "Network Technician",
    ],
    "Sales & Business Development": [
        "Sales Executive",
        "Business Development Executive",
        "Sales Manager",
        "Marketing Executive",
    ],
    "Client Relations": [
        "Client Relationship Executive",
        "Customer Support Executive",
        "Client Relationship Manager",
    ],
    "Procurement & Inventory": [
        "Procurement Executive",
        "Purchase Manager",
        "Storekeeper",
        "Inventory Coordinator",
    ],
    "Finance & Accounts": [
        "Accountant",
        "Accounts Executive",
        "Finance Manager",
    ],
    "HR & Recruitment": [
        "HR Executive",
        "Recruiter",
        "HR Manager",
    ],
    "Marketing & SEO": [
        "SEO Executive",
        "Digital Marketing Executive",
        "Content Marketing Executive",
        "SEO Manager",
    ],
    "IT & Systems": [
        "IT Support Engineer",
        "System Administrator",
        "Software Developer",
        "IT Manager",
    ],
    "Quality & Safety": [
        "Quality Engineer",
        "Safety Officer",
        "QA/QC Engineer",
        "Safety Manager",
    ],
    "Media & Content": [
        "Graphic Designer",
        "Video Editor",
        "Content Writer",
        "Media Coordinator",
    ],
    "ECE": [
        "ECE Engineer",
        "Electronics Engineer",
        "Embedded Systems Engineer",
        "IoT Engineer",
    ],
}


# =========================================================
# MODULES AND PERMISSIONS
# =========================================================

MODULES = [
    "dashboard",
    "projects",
    "services",
    "testimonials",
    "leads",
    "project_tracker",
    "media",
    "contacts",
    "seo",
    "backups",
    "users",
]

ACTIONS = ["view", "create", "edit", "delete"]

# These are the modules that Super Admin may assign to
# Staff and Admin accounts.
#
# Backups and User Management are intentionally excluded.
ADMIN_DELEGABLE_MODULES = [
    "dashboard",
    "projects",
    "services",
    "testimonials",
    "leads",
    "project_tracker",
    "media",
    "contacts",
    "seo",
]

ADMIN_DEFAULT_PERMISSIONS = {
    module: ["view"]
    for module in ADMIN_DELEGABLE_MODULES
}


# =========================================================
# PERMISSION FUNCTIONS
# =========================================================

def effective_permissions(user):
    if not user or not user.is_authenticated:
        return {}

    # Super Admin has complete access.
    if getattr(user, "role", None) == "super_admin":
        return {
            module: ACTIONS.copy()
            for module in MODULES
        }

    permissions = getattr(user, "permissions", None)

    # Older Admin accounts without a saved permissions value
    # receive the previous default view permissions.
    if permissions is None:
        if getattr(user, "role", None) == "admin":
            return {
                module: actions.copy()
                for module, actions in ADMIN_DEFAULT_PERMISSIONS.items()
            }

        return {}

    if isinstance(permissions, str):
        try:
            permissions = json.loads(permissions)
        except (ValueError, TypeError):
            return {}

    if not isinstance(permissions, dict):
        return {}

    # Only accept known modules and actions.
    cleaned = {}

    for module, selected_actions in permissions.items():
        if module not in ADMIN_DELEGABLE_MODULES:
            continue

        if not isinstance(selected_actions, list):
            continue

        valid_actions = [
            action
            for action in selected_actions
            if action in ACTIONS
        ]

        if valid_actions:
            cleaned[module] = valid_actions

    return cleaned


def can_access(user, module, action="view"):
    if not user or not user.is_authenticated:
        return False

    if getattr(user, "role", None) == "super_admin":
        return True

    if module not in MODULES or action not in ACTIONS:
        return False

    permissions = effective_permissions(user)

    return action in permissions.get(module, [])


def permission_required(module, action="view"):
    def decorator(view_function):

        @wraps(view_function)
        @login_required
        def wrapped_view(*args, **kwargs):

            if not can_access(current_user, module, action):
                abort(403)

            return view_function(*args, **kwargs)

        return wrapped_view

    return decorator


def user_management_required(view_function):
    @wraps(view_function)
    @login_required
    def wrapped_view(*args, **kwargs):

        if getattr(current_user, "role", None) != "super_admin":
            abort(403)

        return view_function(*args, **kwargs)

    return wrapped_view


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def module_page(title, description, template="module.html"):
    return render_template(
        template,
        title=title,
        description=description,
    )


def read_permissions_from_form():
    permissions = {}

    for module in ADMIN_DELEGABLE_MODULES:

        selected = request.form.getlist(
            f"permissions_{module}"
        )

        valid_actions = [
            action
            for action in selected
            if action in ACTIONS
        ]

        if valid_actions:
            permissions[module] = valid_actions

    return permissions


def valid_department_and_job(department, job_title):
    return (
        department in DEPARTMENTS
        and isinstance(job_title, str)
        and job_title.strip() in DEPARTMENTS.get(department, [])
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@admin.route("/")
@admin.route("/dashboard")
@permission_required("dashboard", "view")
def dashboard():

    stats = {
        "users": User.query.count(),
        "projects": Project.query.count(),
        "services": Service.query.count(),
        "testimonials": Testimonial.query.count(),

        "pending_testimonials": Testimonial.query.filter(
            Testimonial.is_approved.is_(False)
        ).count(),

        "leads": Lead.query.count(),

        "new_leads": Lead.query.filter(
            db.func.lower(Lead.status) == "new"
        ).count(),

        "media": Media.query.count(),
        "messages": ContactMessage.query.count(),
    }

    return render_template(
        "dashboard.html",
        stats=stats,
        users_count=stats["users"],
        projects_count=stats["projects"],
        services_count=stats["services"],
        testimonials_count=stats["testimonials"],
        leads_count=stats["leads"],
        media_count=stats["media"],
        messages_count=stats["messages"],
    )


# =========================================================
# PROJECTS
# =========================================================

@admin.route("/projects")
@permission_required("projects", "view")
def projects():

    records = Project.query.order_by(
        Project.id.desc()
    ).all()

    return render_template(
        "projects.html",
        projects=records,
    )


# =========================================================
# SERVICES
# =========================================================

@admin.route("/services")
@permission_required("services", "view")
def services():

    return module_page(
        "Services",
        "Manage website services.",
    )


# =========================================================
# TESTIMONIALS
# =========================================================

@admin.route("/testimonials")
@permission_required("testimonials", "view")
def testimonials():

    return module_page(
        "Testimonials",
        "Manage website testimonials.",
    )


# =========================================================
# LEADS
# =========================================================

@admin.route("/leads")
@permission_required("leads", "view")
def leads():

    return module_page(
        "Leads",
        "Manage customer enquiries and leads.",
    )


# =========================================================
# PROJECT TRACKER
# =========================================================

@admin.route("/project-tracker")
@permission_required("project_tracker", "view")
def project_tracker():

    return module_page(
        "Project Tracker",
        "Track construction projects.",
    )


# =========================================================
# MEDIA
# =========================================================

@admin.route("/media")
@permission_required("media", "view")
def media():

    return module_page(
        "Media Library",
        "Manage website media files.",
    )


# =========================================================
# CONTACTS
# =========================================================

@admin.route("/contacts")
@permission_required("contacts", "view")
def contacts():

    return module_page(
        "Contact Hub",
        "Manage contact messages.",
    )


# =========================================================
# SEO SETTINGS
# =========================================================

@admin.route("/seo", methods=["GET", "POST"])
@permission_required("seo", "view")
def seo():

    if request.method == "POST":

        if not can_access(current_user, "seo", "edit"):
            abort(403)

        flash(
            "SEO settings form submitted. "
            "Connect your existing SEO model fields to save changes.",
            "info",
        )

        return redirect(url_for("admin.seo"))

    return module_page(
        "SEO Settings",
        "Manage your website SEO settings.",
    )


# =========================================================
# DATABASE BACKUPS
# =========================================================

@admin.route("/backups")
@permission_required("backups", "view")
def backups():

    return redirect(url_for("backups.index"))


# =========================================================
# USER MANAGEMENT
# =========================================================

@admin.route("/users")
@user_management_required
def users():

    records = User.query.order_by(
        User.id.desc()
    ).all()

    return render_template(
        "users.html",
        users=records,
        departments=DEPARTMENTS,
        modules=ADMIN_DELEGABLE_MODULES,
        admin_delegable_modules=ADMIN_DELEGABLE_MODULES,
        actions=ACTIONS,
        current_role=current_user.role,
        role_presets={},
    )


# =========================================================
# CREATE USER
# =========================================================

@admin.route("/users/create", methods=["POST"])
@user_management_required
def create_user():

    name = (
        request.form.get("name")
        or request.form.get("username")
        or ""
    ).strip()

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    role = request.form.get("role", "staff").strip()

    department = request.form.get(
        "department", ""
    ).strip()

    job_title = request.form.get(
        "job_title", ""
    ).strip()

    if not name or not email or not password:
        flash(
            "Name, email and password are required.",
            "error",
        )
        return redirect(url_for("admin.users"))

    if role not in ["admin", "staff"]:
        flash("Invalid user role.", "error")
        return redirect(url_for("admin.users"))

    if User.query.filter_by(email=email).first():
        flash("Email address already exists.", "error")
        return redirect(url_for("admin.users"))

    if not valid_department_and_job(department, job_title):
        flash(
            "Select a valid department and job title.",
            "error",
        )
        return redirect(url_for("admin.users"))

    if len(password) < 12:
        flash(
            "Password must contain at least 12 characters.",
            "error",
        )
        return redirect(url_for("admin.users"))

    user = User(
        name=name,
        email=email,
        role=role,
        department=department,
        job_title=job_title,
    )

    user.set_password(password)

    # Save the exact permissions selected by Super Admin.
    user.permissions = read_permissions_from_form()

    try:
        db.session.add(user)
        db.session.commit()

        flash("User created successfully.", "success")

    except Exception:
        db.session.rollback()

        flash(
            "Unable to create user. Check the submitted details.",
            "error",
        )

    return redirect(url_for("admin.users"))


# =========================================================
# EDIT USER
# =========================================================

@admin.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@user_management_required
def edit_user(user_id):

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash(
            "You cannot edit your own account here.",
            "error",
        )
        return redirect(url_for("admin.users"))

    if user.role == "super_admin":
        abort(403)

    if request.method == "POST":

        name = (
            request.form.get("name")
            or request.form.get("username")
            or user.name
        ).strip()

        email = request.form.get(
            "email",
            user.email,
        ).strip().lower()

        department = request.form.get(
            "department",
            "",
        ).strip()

        job_title = request.form.get(
            "job_title",
            "",
        ).strip()

        role = request.form.get(
            "role",
            user.role,
        ).strip()

        if not name or not email:
            flash("Name and email are required.", "error")
            return redirect(
                url_for("admin.edit_user", user_id=user.id)
            )

        if role not in ["admin", "staff"]:
            flash("Invalid role.", "error")
            return redirect(
                url_for("admin.edit_user", user_id=user.id)
            )

        if not valid_department_and_job(department, job_title):
            flash(
                "Invalid department or job title.",
                "error",
            )
            return redirect(
                url_for("admin.edit_user", user_id=user.id)
            )

        existing_email = User.query.filter(
            User.email == email,
            User.id != user.id,
        ).first()

        if existing_email:
            flash(
                "That email address is already used by another account.",
                "error",
            )
            return redirect(
                url_for("admin.edit_user", user_id=user.id)
            )

        user.name = name
        user.email = email
        user.role = role
        user.department = department
        user.job_title = job_title

        # Update the selected permissions.
        user.permissions = read_permissions_from_form()

        new_password = request.form.get("password", "")

        if new_password:
            if len(new_password) < 12:
                flash(
                    "Password must contain at least 12 characters.",
                    "error",
                )
                return redirect(
                    url_for("admin.edit_user", user_id=user.id)
                )

            user.set_password(new_password)

        try:
            db.session.commit()

            flash("User updated successfully.", "success")
            return redirect(url_for("admin.users"))

        except Exception:
            db.session.rollback()

            flash(
                "Unable to update user. Check the submitted details.",
                "error",
            )

            return redirect(
                url_for("admin.edit_user", user_id=user.id)
            )

    return render_template(
        "edit_user.html",
        user=user,
        departments=DEPARTMENTS,
        modules=ADMIN_DELEGABLE_MODULES,
        admin_delegable_modules=ADMIN_DELEGABLE_MODULES,
        actions=ACTIONS,
        current_role=current_user.role,
    )


# =========================================================
# ACTIVATE / DEACTIVATE USER
# =========================================================

@admin.route(
    "/users/<int:user_id>/toggle-status",
    methods=["POST"],
)
@user_management_required
def toggle_user_status(user_id):

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash(
            "You cannot deactivate your own account.",
            "error",
        )
        return redirect(url_for("admin.users"))

    if user.role == "super_admin":
        abort(403)

    if not hasattr(user, "is_active"):
        flash(
            "This User model does not support account status changes.",
            "error",
        )
        return redirect(url_for("admin.users"))

    user.is_active = not user.is_active

    try:
        db.session.commit()

        flash("User status updated.", "success")

    except Exception:
        db.session.rollback()

        flash(
            "Unable to update user status.",
            "error",
        )

    return redirect(url_for("admin.users"))


# =========================================================
# COMPATIBILITY ROUTES
# =========================================================

@admin.route("/media-library")
@permission_required("media", "view")
def media_library():

    return redirect(url_for("admin.media"))


@admin.route("/contact-hub")
@permission_required("contacts", "view")
def contact_hub():

    return redirect(url_for("admin.contacts"))


@admin.route("/seo-settings")
@permission_required("seo", "view")
def seo_settings():

    return redirect(url_for("admin.seo"))