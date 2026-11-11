
import csv
import json
import os
import uuid

from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
from functools import wraps

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    current_app,
    send_file,
)

from flask_login import login_required, current_user

from werkzeug.utils import secure_filename

from sqlalchemy.inspection import inspect

from openpyxl import Workbook

from .models import ExtractionJob, ExtractionRecord
from .engine import extract_file

from app.extensions import db

from app.models import (
    Lead,
    ContactMessage,
    Enquiry,
    CareerApplication,
    Testimonial,
    Project,
    Service,
    Customer,
    Media,
)


# =====================================================
# BLUEPRINT
# =====================================================

extraction = Blueprint(
    "extraction",
    __name__,
    url_prefix="/admin/extraction"
)


# =====================================================
# CONFIGURATION
# =====================================================

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_DATABASE_SOURCES = {
    "leads": Lead,
    "contact_messages": ContactMessage,
    "enquiries": Enquiry,
    "career_applications": CareerApplication,
    "testimonials": Testimonial,
    "projects": Project,
    "services": Service,
    "customers": Customer,
    "media": Media,
}


# =====================================================
# ACCESS CONTROL
# =====================================================

def extraction_access(view_function):

    @wraps(view_function)
    @login_required
    def wrapper(*args, **kwargs):

        if current_user.role not in ("super_admin", "admin"):
            abort(403)

        if not current_user.is_active:
            abort(403)

        return view_function(*args, **kwargs)

    return wrapper


# =====================================================
# FILE STORAGE
# =====================================================

def get_upload_directory():

    upload_directory = (
        Path(current_app.instance_path)
        / "extraction_uploads"
    )

    upload_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    return upload_directory


def allowed_file(filename):

    extension = Path(filename).suffix.lower()

    return extension in ALLOWED_EXTENSIONS


# =====================================================
# DATABASE SERIALIZATION
# =====================================================

def serialize_model(record):

    result = {}

    mapper = inspect(record.__class__)

    for column in mapper.columns:

        value = getattr(record, column.key)

        if isinstance(value, datetime):
            value = value.isoformat()

        result[column.key] = value

    return result


# =====================================================
# CREATE EXTRACTION RECORD
# =====================================================

def create_extraction_record(job, extracted_data):

    record = ExtractionRecord(
        job_id=job.id,
        extracted_data=extracted_data,
        review_status="pending"
    )

    db.session.add(record)

    return record


# =====================================================
# EXTRACTION DASHBOARD
# =====================================================

@extraction.route("/", methods=["GET"])
@extraction_access
def index():

    jobs = ExtractionJob.query.order_by(
        ExtractionJob.created_at.desc()
    ).limit(100).all()

    pending_count = ExtractionRecord.query.filter_by(
        review_status="pending"
    ).count()

    approved_count = ExtractionRecord.query.filter_by(
        review_status="approved"
    ).count()

    rejected_count = ExtractionRecord.query.filter_by(
        review_status="rejected"
    ).count()

    return render_template(
        "extraction/index.html",
        jobs=jobs,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        sources=sorted(ALLOWED_DATABASE_SOURCES.keys())
    )


# =====================================================
# UPLOAD AND EXTRACT FILE
# =====================================================

@extraction.route("/upload", methods=["POST"])
@extraction_access
def upload():

    uploaded_file = request.files.get("file")

    if not uploaded_file or not uploaded_file.filename:
        flash("Please select a file.", "error")
        return redirect(url_for("extraction.index"))

    original_name = secure_filename(
        uploaded_file.filename
    )

    if not original_name:
        flash("Invalid filename.", "error")
        return redirect(url_for("extraction.index"))

    if not allowed_file(original_name):
        flash("Unsupported file format.", "error")
        return redirect(url_for("extraction.index"))

    # Check actual uploaded size.
    uploaded_file.stream.seek(0, os.SEEK_END)
    file_size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)

    if file_size == 0:
        flash("The uploaded file is empty.", "error")
        return redirect(url_for("extraction.index"))

    if file_size > MAX_FILE_SIZE:
        flash("Maximum upload size is 10 MB.", "error")
        return redirect(url_for("extraction.index"))

    extension = Path(original_name).suffix.lower()

    stored_name = f"{uuid.uuid4().hex}{extension}"

    upload_directory = get_upload_directory()

    file_path = upload_directory / stored_name

    job = ExtractionJob(
        filename=original_name,
        stored_filename=stored_name,
        file_type=extension,
        source_type="file",
        status="processing",
        uploaded_by=current_user.id
    )

    try:

        uploaded_file.save(str(file_path))

        db.session.add(job)
        db.session.flush()

        extracted_text = extract_file(str(file_path))

        if not extracted_text or not extracted_text.strip():
            raise ValueError(
                "No readable text was found in the file."
            )

        # Store extracted text in staging.
        job.extracted_text = extracted_text
        job.status = "completed"

        create_extraction_record(
            job,
            {
                "source_file": original_name,
                "file_type": extension,
                "text": extracted_text
            }
        )

        db.session.commit()

        flash(
            "File extracted successfully. Please review the result.",
            "success"
        )

        return redirect(
            url_for(
                "extraction.review",
                job_id=job.id
            )
        )

    except Exception as error:

        db.session.rollback()

        # Remove failed upload from disk.
        if file_path.exists():
            file_path.unlink()

        current_app.logger.exception(
            "Extraction failed"
        )

        flash(
            f"Extraction failed: {str(error)}",
            "error"
        )

        return redirect(url_for("extraction.index"))


# =====================================================
# EXTRACT WEBSITE / MYSQL DATA
# =====================================================

@extraction.route("/database", methods=["POST"])
@extraction_access
def extract_database():

    source_name = request.form.get(
        "source",
        ""
    ).strip()

    if source_name not in ALLOWED_DATABASE_SOURCES:
        flash("Invalid database source.", "error")
        return redirect(url_for("extraction.index"))

    model = ALLOWED_DATABASE_SOURCES[source_name]

    job = ExtractionJob(
        filename=f"MySQL: {source_name}",
        stored_filename=f"database-{uuid.uuid4().hex}",
        file_type="database",
        source_type="database",
        status="processing",
        uploaded_by=current_user.id
    )

    try:

        db.session.add(job)
        db.session.flush()

        records = model.query.limit(500).all()

        for item in records:

            extracted_data = {
                "source_table": source_name,
                "record": serialize_model(item)
            }

            create_extraction_record(
                job,
                extracted_data
            )

        job.extracted_text = (
            f"Extracted {len(records)} records "
            f"from {source_name}."
        )

        job.status = "completed"

        db.session.commit()

        flash(
            f"Extracted {len(records)} records from {source_name}.",
            "success"
        )

        return redirect(
            url_for(
                "extraction.review",
                job_id=job.id
            )
        )

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Database extraction failed"
        )

        flash(
            "Database extraction failed. Check the application logs.",
            "error"
        )

        return redirect(url_for("extraction.index"))


# =====================================================
# WEBSITE DATA EXTRACTION
# =====================================================

@extraction.route("/website", methods=["POST"])
@extraction_access
def extract_website():

    source_name = request.form.get(
        "source",
        ""
    ).strip()

    if source_name not in ALLOWED_DATABASE_SOURCES:
        flash("Invalid website data source.", "error")
        return redirect(url_for("extraction.index"))

    return redirect(
        url_for(
            "extraction.extract_database"
        ),
        code=307
    )


# =====================================================
# REVIEW EXTRACTION JOB
# =====================================================

@extraction.route("/review/<int:job_id>", methods=["GET"])
@extraction_access
def review(job_id):

    job = ExtractionJob.query.get_or_404(job_id)

    records = ExtractionRecord.query.filter_by(
        job_id=job.id
    ).order_by(
        ExtractionRecord.id.asc()
    ).all()

    return render_template(
        "extraction/review.html",
        job=job,
        records=records
    )


# =====================================================
# EDIT EXTRACTED DATA
# =====================================================

@extraction.route(
    "/record/<int:record_id>/edit",
    methods=["POST"]
)
@extraction_access
def edit_record(record_id):

    record = ExtractionRecord.query.get_or_404(
        record_id
    )

    if record.review_status != "pending":
        flash(
            "Only pending records can be edited.",
            "error"
        )

        return redirect(
            url_for(
                "extraction.review",
                job_id=record.job_id
            )
        )

    submitted_data = request.form.get(
        "extracted_data",
        ""
    )

    try:

        updated_data = json.loads(submitted_data)

        if not isinstance(updated_data, dict):
            raise ValueError("Expected a JSON object.")

        record.extracted_data = updated_data

        db.session.commit()

        flash(
            "Extracted data updated successfully.",
            "success"
        )

    except (ValueError, TypeError, json.JSONDecodeError):

        db.session.rollback()

        flash(
            "Invalid JSON data. Changes were not saved.",
            "error"
        )

    return redirect(
        url_for(
            "extraction.review",
            job_id=record.job_id
        )
    )


# =====================================================
# APPROVE RECORD
# =====================================================

@extraction.route(
    "/record/<int:record_id>/approve",
    methods=["POST"]
)
@extraction_access
def approve_record(record_id):

    record = ExtractionRecord.query.get_or_404(
        record_id
    )

    if record.review_status != "pending":
        flash(
            "This record has already been reviewed.",
            "error"
        )

        return redirect(
            url_for(
                "extraction.review",
                job_id=record.job_id
            )
        )

    record.review_status = "approved"
    record.reviewed_by = current_user.id
    record.reviewed_at = datetime.utcnow()

    try:

        db.session.commit()

        flash(
            "Record approved successfully.",
            "success"
        )

    except Exception:

        db.session.rollback()

        flash(
            "Unable to approve this record.",
            "error"
        )

    return redirect(
        url_for(
            "extraction.review",
            job_id=record.job_id
        )
    )


# =====================================================
# REJECT RECORD
# =====================================================

@extraction.route(
    "/record/<int:record_id>/reject",
    methods=["POST"]
)
@extraction_access
def reject_record(record_id):

    record = ExtractionRecord.query.get_or_404(
        record_id
    )

    if record.review_status != "pending":
        flash(
            "This record has already been reviewed.",
            "error"
        )

        return redirect(
            url_for(
                "extraction.review",
                job_id=record.job_id
            )
        )

    record.review_status = "rejected"
    record.reviewed_by = current_user.id
    record.reviewed_at = datetime.utcnow()

    try:

        db.session.commit()

        flash(
            "Record rejected.",
            "success"
        )

    except Exception:

        db.session.rollback()

        flash(
            "Unable to reject this record.",
            "error"
        )

    return redirect(
        url_for(
            "extraction.review",
            job_id=record.job_id
        )
    )


# =====================================================
# EXPORT CSV
# =====================================================

@extraction.route("/export/csv", methods=["GET"])
@extraction_access
def export_csv():

    status = request.args.get(
        "status",
        "approved"
    )

    if status not in ("approved", "pending", "rejected", "all"):
        abort(400)

    query = ExtractionRecord.query

    if status != "all":
        query = query.filter_by(
            review_status=status
        )

    records = query.order_by(
        ExtractionRecord.created_at.desc()
    ).all()

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "Record ID",
        "Job ID",
        "Review Status",
        "Extracted Data",
        "Created At"
    ])

    for record in records:

        writer.writerow([
            record.id,
            record.job_id,
            record.review_status,
            json.dumps(
                record.extracted_data,
                ensure_ascii=False
            ),
            record.created_at.isoformat()
            if record.created_at else ""
        ])

    memory_file = BytesIO(
        output.getvalue().encode("utf-8-sig")
    )

    memory_file.seek(0)

    return send_file(
        memory_file,
        mimetype="text/csv",
        as_attachment=True,
        download_name="lum_tek_extraction.csv"
    )


# =====================================================
# EXPORT EXCEL
# =====================================================

@extraction.route("/export/excel", methods=["GET"])
@extraction_access
def export_excel():

    status = request.args.get(
        "status",
        "approved"
    )

    if status not in ("approved", "pending", "rejected", "all"):
        abort(400)

    query = ExtractionRecord.query

    if status != "all":
        query = query.filter_by(
            review_status=status
        )

    records = query.order_by(
        ExtractionRecord.created_at.desc()
    ).all()

    workbook = Workbook()

    sheet = workbook.active
    sheet.title = "Extracted Data"

    sheet.append([
        "Record ID",
        "Job ID",
        "Review Status",
        "Extracted Data",
        "Created At"
    ])

    for record in records:

        sheet.append([
            record.id,
            record.job_id,
            record.review_status,
            json.dumps(
                record.extracted_data,
                ensure_ascii=False
            ),
            record.created_at.isoformat()
            if record.created_at else ""
        ])

    output = BytesIO()

    workbook.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        as_attachment=True,
        download_name="lum_tek_extraction.xlsx"
    )
