
from datetime import datetime

from app.extensions import db


class ExtractionJob(db.Model):
    __tablename__ = "extraction_jobs"

    id = db.Column(db.Integer, primary_key=True)

    filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)

    source_type = db.Column(
        db.String(30),
        nullable=False,
        default="file"
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="pending"
    )

    extracted_text = db.Column(db.Text)

    error_message = db.Column(db.Text)

    uploaded_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    records = db.relationship(
        "ExtractionRecord",
        backref="job",
        cascade="all, delete-orphan",
        lazy=True
    )


class ExtractionRecord(db.Model):
    __tablename__ = "extraction_records"

    id = db.Column(db.Integer, primary_key=True)

    job_id = db.Column(
        db.Integer,
        db.ForeignKey("extraction_jobs.id"),
        nullable=False
    )

    extracted_data = db.Column(
        db.JSON,
        nullable=False,
        default=dict
    )

    review_status = db.Column(
        db.String(30),
        nullable=False,
        default="pending"
    )

    reviewed_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    reviewed_at = db.Column(db.DateTime)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )
