#!/usr/bin/env python3
"""Script to test the database connection."""

import logging
import os
import sys
import time

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from farsight2.database.db import engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def test_connection(max_retries=5, retry_interval=5):
    """Test the database connection."""
    retries = 0
    while retries < max_retries:
        try:
            # Try to connect to the database
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info(f"Database connection successful: {result.scalar()}")
                
                # Check if pgvector is installed
                result = conn.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"))
                if result.scalar():
                    logger.info("pgvector extension is installed")
                else:
                    logger.warning("pgvector extension is not installed")
                
                return True
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            retries += 1
            if retries < max_retries:
                logger.info(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
    
    logger.error(f"Failed to connect to database after {max_retries} retries")
    return False

if __name__ == "__main__":
    test_connection() 