
from functools import wraps

from flask import Blueprint, abort, render_template
from flask_login import login_required, current_user

from .models import (
    User,
    Project,
    Service,
    Testimonial,
    Lead,
    Media,
    ContactMessage
)

admin = Blueprint("admin", __name__, url_prefix="/admin")


# -----------------------------------------
# ROLE-BASED ACCESS CONTROL
# -----------------------------------------

def roles_required(*allowed_roles):

    def decorator(view_function):

        @wraps(view_function)
        @login_required
        def wrapped(*args, **kwargs):

            if current_user.role not in allowed_roles:
                abort(403)

            return view_function(*args, **kwargs)

        return wrapped

    return decorator


# -----------------------------------------
# DASHBOARD
# -----------------------------------------

@admin.route("/")
@roles_required("admin", "project_manager", "blogger")
def dashboard():

    stats = {
        "users": User.query.count(),

        "projects": Project.query.count(),

        "services": Service.query.count(),

        "testimonials": Testimonial.query.count(),

        "pending_testimonials": Testimonial.query.filter_by(
            is_approved=False
        ).count(),

        "leads": Lead.query.count(),

        "new_leads": Lead.query.filter_by(
            status="new"
        ).count(),

        "media": Media.query.count(),

        "messages": ContactMessage.query.count()
    }

    return render_template(
        "dashboard.html",
        stats=stats
    )


# -----------------------------------------
# PROJECTS MANAGEMENT
# -----------------------------------------

@admin.route("/projects")
@roles_required("admin", "project_manager", "blogger")
def projects():

    all_projects = Project.query.order_by(
        Project.created_at.desc()
    ).all()

    return render_template(
        "projects.html",
        projects=all_projects
    )


# -----------------------------------------
# SERVICES MANAGEMENT
# -----------------------------------------

@admin.route("/services")
@roles_required("admin", "project_manager", "blogger")
def services():

    return module_page(
        "Services Management",
        "Manage residential, commercial, roofing and CCTV services."
    )


# -----------------------------------------
# TESTIMONIALS
# -----------------------------------------

@admin.route("/testimonials")
@roles_required("admin", "project_manager")
def testimonials():

    return module_page(
        "Testimonials",
        "Review, approve and feature customer testimonials."
    )


# -----------------------------------------
# QUOTE REQUESTS
# -----------------------------------------

@admin.route("/leads")
@roles_required("admin", "project_manager")
def leads():

    return module_page(
        "Quote Requests",
        "View and manage customer quotation requests."
    )


# -----------------------------------------
# PROJECT TRACKER
# -----------------------------------------

@admin.route("/project-tracker")
@roles_required("admin", "project_manager")
def project_tracker():

    return module_page(
        "Project Tracker",
        "Manage weekly project progress updates."
    )


# -----------------------------------------
# MEDIA LIBRARY
# -----------------------------------------

@admin.route("/media")
@roles_required("admin", "project_manager", "blogger")
def media_library():

    return module_page(
        "Media Library",
        "Manage project photographs and uploaded media."
    )


# -----------------------------------------
# CONTACT HUB
# -----------------------------------------

@admin.route("/contacts")
@roles_required("admin", "project_manager")
def contact_hub():

    return module_page(
        "Contact Hub",
        "Manage customer, subcontractor and applicant messages."
    )


# -----------------------------------------
# SEO SETTINGS
# -----------------------------------------

@admin.route("/seo")
@roles_required("admin", "blogger")
def seo_settings():

    return module_page(
        "SEO Settings",
        "Manage website page titles, descriptions and keywords."
    )


# -----------------------------------------
# DATABASE BACKUPS
# -----------------------------------------

@admin.route("/backups")
@roles_required("admin")
def backups():

    return module_page(
        "Database Backups",
        "Manage database backup records."
    )


# -----------------------------------------
# USER MANAGEMENT
# -----------------------------------------

@admin.route("/users")
@roles_required("admin")
def users():

    return module_page(
        "User Management",
        "Manage administrator, project manager and blogger accounts."
    )


# -----------------------------------------
# SHARED MODULE TEMPLATE
# -----------------------------------------

def module_page(title, description):

    return render_template(
        "module.html",
        page_title=title,
        page_description=description
    )
