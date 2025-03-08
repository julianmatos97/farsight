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
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("farsight2.log")
    ]
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

def generate_test_suite(company: str, years: List[int], name: str):
    """
    Generate a test suite for a company and years.
    
    Args:
        company: Company ticker or name
        years: List of years to include in the test suite
        name: Name for the test suite
    """
    # Initialize the database
    init_db()
    
    # Check for OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        sys.exit(1)
    
    # Generate test suite
    generator = TestSuiteGenerator(api_key=api_key)
    test_suite = generator.generate_test_suite(company, years, name)
    
    # Log results
    logger.info(f"Generated test suite with {len(test_suite.questions)} questions")
    for i, question in enumerate(test_suite.questions):
        logger.info(f"Question {i+1}: {question}")

def run_evaluation(test_suite_name: str, evaluation_name: str):
    """
    Run an evaluation on a test suite.
    
    Args:
        test_suite_name: Name of the test suite to evaluate
        evaluation_name: Name for the evaluation results
    """
    # Initialize the database
    init_db()
    
    # Check for OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        sys.exit(1)
    
    # Load the test suite
    test_suite_dir = os.path.join(os.path.dirname(__file__), "../data/test_suites")
    test_suite_path = os.path.join(test_suite_dir, f"{test_suite_name}_test_suite.json")
    
    if not os.path.exists(test_suite_path):
        logger.error(f"Test suite not found: {test_suite_path}")
        sys.exit(1)
    
    # Parse test suite JSON
    import json
    with open(test_suite_path, 'r', encoding='utf-8') as f:
        test_suite_data = json.load(f)
    
    # Create test suite object
    from farsight2.models.models import TestSuite
    test_suite = TestSuite(
        questions=test_suite_data["questions"],
        expected_answers=test_suite_data["expected_answers"]
    )
    
    # Create an API client for testing
    class APIClient:
        def __init__(self, base_url: str):
            self.base_url = base_url
        
        def query(self, query: str) -> Dict[str, Any]:
            """Send a query to the API and return the response"""
            import requests
            response = requests.post(
                f"{self.base_url}/query",
                json={"query": query}
            )
            response.raise_for_status()
            return response.json()
    
    api_client = APIClient("http://localhost:8000")
    
    # Run the evaluation
    evaluator = Evaluator(api_client, api_key=api_key)
    evaluation_results = evaluator.evaluate_test_suite(test_suite, evaluation_name)
    
    # Print the results
    logger.info(f"Evaluation results:")
    for key, value in evaluation_results.metrics.items():
        logger.info(f"{key}: {value}")

def init_database():
    """Initialize the database schema and tables."""
    init_db()
    logger.info("Database initialized")

def main():
    """
    Main entry point for the application.
    
    Parses command line arguments and runs the appropriate function.
    """
    parser = argparse.ArgumentParser(description="Farsight2 - 10-K/10-Q Digestion and Retrieval System")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # API command
    api_parser = subparsers.add_parser("api", help="Run the API server")
    
    # Test suite command
    test_suite_parser = subparsers.add_parser("test-suite", help="Generate a test suite")
    test_suite_parser.add_argument("--company", required=True, help="Company ticker or name")
    test_suite_parser.add_argument("--years", required=True, nargs="+", type=int, help="Years to cover")
    test_suite_parser.add_argument("--name", required=True, help="Name for the test suite")
    
    # Evaluation command
    evaluation_parser = subparsers.add_parser("evaluate", help="Run an evaluation")
    evaluation_parser.add_argument("--test-suite", required=True, help="Name of the test suite")
    evaluation_parser.add_argument("--name", required=True, help="Name for the evaluation results")
    
    # Init database command
    init_db_parser = subparsers.add_parser("init-db", help="Initialize the database")
    
    args = parser.parse_args()
    
    # Run the appropriate command
    if args.command == "api":
        run_api()
    elif args.command == "test-suite":
        generate_test_suite(args.company, args.years, args.name)
    elif args.command == "evaluate":
        run_evaluation(args.test_suite, args.name)
    elif args.command == "init-db":
        init_database()
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 