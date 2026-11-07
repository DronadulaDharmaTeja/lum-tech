
from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine

app = FastAPI(
    title="LUM TEK API",
    description="Construction Company Management System",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Welcome to LUM TEK API",
        "status": "running"
    }


@app.get("/health/db")
def database_health():

    try:
        with engine.connect() as connection:

            database_name = connection.execute(
                text("SELECT DATABASE()")
            ).scalar()

            test_query = connection.execute(
                text("SELECT 1")
            ).scalar()

        return {
            "status": "connected",
            "database": database_name,
            "test_query": test_query
        }

    except SQLAlchemyError as error:

        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Check MySQL credentials and server."
        )
