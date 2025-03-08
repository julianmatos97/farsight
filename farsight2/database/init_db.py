"""Initialize the database."""

import logging

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