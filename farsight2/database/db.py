"""
Database connection and initialization.

This module provides functions for connecting to the database
and initializing the database schema.
"""

import os
import logging
from typing import Any, Dict
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from farsight2.config import DATABASE_URL

# Set up logging
logger = logging.getLogger(__name__)


# Create engine and session

# Create engine and session
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # Increase from default 5
    max_overflow=20,  # Increase from default 10
    pool_timeout=60,  # Increase timeout from 30 seconds
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Verify connections before using them
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db_session():
    """
    Get a database session.

    Returns:
        SQLAlchemy session object
    """
    session = SessionLocal()
    try:
        return session
    finally:
        session.close()


def test_connection():
    """Test database connection and provide helpful message if it fails."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()")).scalar()
            logger.info(f"Connected to database: {result}")
            return True
    except Exception as e:
        if "connection to server" in str(e) and "localhost" in str(e):
            logger.error(
                f"Database connection error: {str(e)}\n"
                "If running outside Docker, make sure PostgreSQL is running locally.\n"
                "Or set DATABASE_URL environment variable to point to your database."
            )
        else:
            logger.error(f"Database connection error: {str(e)}")
        return False


def init_db():
    """
    Initialize the database schema.

    This function checks if the database is properly set up and
    creates the necessary tables if they don't exist.
    """
    if not test_connection():
        raise Exception("Failed to connect to database")

    # Import models here to avoid circular imports

    # Create tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def get_connection_params() -> Dict[str, Any]:
    """Get database connection parameters from the DATABASE_URL.

    Returns:
        Dict[str, Any]: Database connection parameters
    """
    # Parse the DATABASE_URL
    if "://" not in DATABASE_URL:
        return {}

    # Split the URL into parts
    url_parts = DATABASE_URL.split("://")[1].split("@")
    auth_parts = url_parts[0].split(":")
    host_parts = url_parts[1].split("/")
    host_port = host_parts[0].split(":")

    # Extract the parameters
    params = {
        "user": auth_parts[0],
        "password": auth_parts[1],
        "host": host_port[0],
        "port": int(host_port[1]) if len(host_port) > 1 else 5432,
        "database": host_parts[1],
    }
    return params

