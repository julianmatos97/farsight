"""Initialize the database."""

import logging
from sqlalchemy import text

# Set up logging
logger = logging.getLogger(__name__)


def init_db():
    """Initialize the database."""
    # Import the models
    from farsight2.database.db import Base, engine, test_connection

    # Test connection
    if not test_connection():
        logger.error("Failed to connect to database")
        return False

    # Ensure pgvector extension is installed
    try:
        with engine.connect() as conn:
            # Check if pgvector is installed
            result = conn.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )
            )
            if not result.scalar():
                logger.info("Installing pgvector extension...")
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                logger.info("pgvector extension installed successfully")
            else:
                logger.info("pgvector extension is already installed")
    except Exception as e:
        logger.error(f"Error installing pgvector extension: {e}")
        return False

    # Create tables
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        return False


if __name__ == "__main__":
    init_db()
