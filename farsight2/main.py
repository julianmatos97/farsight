"""
Main script for running the Farsight2 application.

This module provides command-line interface for:
- Running the API server
- Generating test suites
- Running evaluations
- Initializing the database
"""

import argparse
import logging
import os
import sys
from typing import Dict, List, Any

from farsight2.api.app import app
from farsight2.evaluation.test_suite import TestSuiteGenerator, Evaluator
from farsight2.database.db import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("farsight2.log")],
)
logger = logging.getLogger(__name__)


def run_api():
    """
    Run the FastAPI application.

    This function initializes the database and starts the API server.
    """
    # Initialize the database
    init_db()

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


def init_database():
    """Initialize the database schema and tables."""
    init_db()
    logger.info("Database initialized")


def main():
    """
    Main entry point for the application.

    Parses command line arguments and runs the appropriate function.
    """
    parser = argparse.ArgumentParser(
        description="Farsight2 - 10-K/10-Q Digestion and Retrieval System"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # API command
    api_parser = subparsers.add_parser("api", help="Run the API server")

    # Init database command
    init_db_parser = subparsers.add_parser("init-db", help="Initialize the database")

    args = parser.parse_args()

    # Run the appropriate command
    if args.command == "api":
        run_api()
    elif args.command == "init-db":
        init_database()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
