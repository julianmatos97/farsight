"""Test suite for evaluating the system's performance."""

import logging
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from openai import OpenAI

from farsight2.models.models import (
    TestSuite,
    EvaluationResults
)
from farsight2.database.db import SessionLocal
from farsight2.database.repository import (
    TestSuiteRepository,
    EvaluationRepository
)

logger = logging.getLogger(__name__)

class TestSuiteGenerator:
    """Generator for creating test suites."""
    
    def __init__(self, api_key: Optional[str] = None, output_dir: Optional[str] = None):
        """Initialize the test suite generator.
        
        Args:
            api_key: OpenAI API key
            output_dir: Directory to save test suites
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "../../data/test_suites")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Default model for test suite generation
        self.model = "gpt-4o"
        
        # Database session
        self.db = SessionLocal()
        self.test_suite_repo = TestSuiteRepository(self.db)
    
    def generate_test_suite(self, company: str, years: List[int], name: str) -> TestSuite:
        """Generate a test suite for a company and years.
        
        Args:
            company: Company ticker or name
            years: List of years to cover
            name: Name for the test suite
            
        Returns:
            Generated test suite
        """
        logger.info(f"Generating test suite for {company} for years {years}")
        
        # Generate questions using the LLM
        questions = self._generate_questions(company, years)
        
        # For now, expected answers are empty
        # In a real implementation, you would generate expected answers
        expected_answers = [""] * len(questions)
        
        # Create test suite in the database
        try:
            self.test_suite_repo.create_test_suite(name, questions, expected_answers)
        except Exception as e:
            logger.error(f"Error creating test suite in database: {e}")
        
        # Create test suite model
        test_suite = TestSuite(
            questions=questions,
            expected_answers=expected_answers
        )
        
        # Save the test suite to file (for backward compatibility)
        self._save_test_suite(test_suite, name)
        
        return test_suite
    
    def _generate_questions(self, company: str, years: List[int]) -> List[str]:
        """Generate questions for a company and years using an LLM."""
        try:
            # Create the prompt
            years_str = ", ".join(str(year) for year in years)
            prompt = f"""
            Generate a diverse set of 20 questions that someone might ask about {company}'s financial performance, operations, risks, and strategies for the years {years_str}.
            
            The questions should cover different aspects of the company's 10-K and 10-Q filings, including:
            1. Financial metrics and performance
            2. Business segments and products
            3. Market trends and competition
            4. Risk factors
            5. Management discussion and analysis
            6. Future outlook and strategies
            7. Tables and numerical data
            8. Year-over-year comparisons
            9. Quarterly performance
            10. Specific events or developments
            
            For each question, ensure it is specific, answerable from the filings, and provides value to a financial analyst or investor.
            
            Format your response as a JSON array of strings, with each string being a question.
            """
            
            # Call the LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial analyst assistant that generates insightful questions about company financial filings."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Extract the questions
            if isinstance(result, dict) and "questions" in result:
                questions = result["questions"]
            elif isinstance(result, list):
                questions = result
            else:
                logger.warning("Invalid questions format from LLM")
                questions = []
            
            return questions
        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return []
    
    def _save_test_suite(self, test_suite: TestSuite, name: str) -> None:
        """Save a test suite to disk."""
        # Create a filename
        filename = f"{name}_test_suite.json"
        file_path = os.path.join(self.output_dir, filename)
        
        # Convert to dictionary
        test_suite_dict = {
            "questions": test_suite.questions,
            "expected_answers": test_suite.expected_answers
        }
        
        # Save as JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(test_suite_dict, f, indent=2)
    
    def __del__(self):
        """Close the database session when the object is deleted."""
        if hasattr(self, 'db'):
            self.db.close()

class Evaluator:
    """Evaluator for testing the system's performance."""
    
    def __init__(self, api_client, api_key: Optional[str] = None, output_dir: Optional[str] = None):
        """Initialize the evaluator.
        
        Args:
            api_client: Client for the Farsight2 API
            api_key: OpenAI API key
            output_dir: Directory to save evaluation results
        """
        self.api_client = api_client
        
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "../../data/evaluation_results")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Default model for evaluation
        self.model = "gpt-4o"
        
        # Database session
        self.db = SessionLocal()
        self.test_suite_repo = TestSuiteRepository(self.db)
        self.evaluation_repo = EvaluationRepository(self.db)
    
    def evaluate_test_suite(self, test_suite: TestSuite, name: str) -> EvaluationResults:
        """Evaluate a test suite.
        
        Args:
            test_suite: Test suite to evaluate
            name: Name for the evaluation results
            
        Returns:
            Evaluation results
        """
        logger.info(f"Evaluating test suite with {len(test_suite.questions)} questions")
        
        # Process each question
        actual_answers = []
        for question in test_suite.questions:
            try:
                # Query the API
                response = self.api_client.query(question)
                actual_answers.append(response["response"])
            except Exception as e:
                logger.error(f"Error querying API: {e}")
                actual_answers.append(f"Error: {str(e)}")
        
        # Calculate metrics
        metrics = self._calculate_metrics(test_suite.expected_answers, actual_answers)
        
        # Create evaluation results in the database
        try:
            # Find the test suite in the database
            db_test_suite = self.test_suite_repo.get_test_suite(name.replace("_evaluation", ""))
            if db_test_suite:
                # Create the evaluation result
                self.evaluation_repo.create_evaluation(
                    test_suite_name=db_test_suite.name,
                    name=name,
                    metrics=metrics,
                    questions=test_suite.questions,
                    expected_answers=test_suite.expected_answers,
                    actual_answers=actual_answers
                )
        except Exception as e:
            logger.error(f"Error creating evaluation result in database: {e}")
        
        # Create evaluation results model
        evaluation_results = EvaluationResults(
            metrics=metrics,
            questions=test_suite.questions,
            expected_answers=test_suite.expected_answers,
            actual_answers=actual_answers
        )
        
        # Save the evaluation results to file (for backward compatibility)
        self._save_evaluation_results(evaluation_results, name)
        
        return evaluation_results
    
    def _calculate_metrics(self, expected_answers: List[str], actual_answers: List[str]) -> Dict[str, Any]:
        """Calculate evaluation metrics."""
        # This is a simplified implementation
        # In a real implementation, you would use more sophisticated metrics
        
        metrics = {
            "total_questions": len(expected_answers),
            "answered_questions": sum(1 for answer in actual_answers if not answer.startswith("Error")),
            "error_rate": sum(1 for answer in actual_answers if answer.startswith("Error")) / len(actual_answers) if actual_answers else 0
        }
        
        # If we have expected answers, calculate accuracy
        if any(expected_answers):
            # Use the LLM to evaluate accuracy
            accuracy_scores = self._evaluate_accuracy(expected_answers, actual_answers)
            metrics["accuracy"] = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
        
        return metrics
    
    def _evaluate_accuracy(self, expected_answers: List[str], actual_answers: List[str]) -> List[float]:
        """Evaluate the accuracy of answers using an LLM."""
        accuracy_scores = []
        
        for expected, actual in zip(expected_answers, actual_answers):
            # Skip if expected answer is empty or actual answer is an error
            if not expected or actual.startswith("Error"):
                continue
            
            try:
                # Create the prompt
                prompt = f"""
                Evaluate the accuracy of the following answer compared to the expected answer.
                
                Expected answer: {expected}
                
                Actual answer: {actual}
                
                Rate the accuracy on a scale from 0.0 to 1.0, where:
                - 0.0: Completely incorrect or unrelated
                - 0.5: Partially correct but missing key information or containing inaccuracies
                - 1.0: Fully correct and complete
                
                Respond with a JSON object containing a single key "accuracy" with the numerical score.
                """
                
                # Call the LLM
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a financial analysis evaluator that assesses the accuracy of answers about company financial filings."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                
                # Parse the response
                content = response.choices[0].message.content
                result = json.loads(content)
                
                # Extract the accuracy score
                accuracy = result.get("accuracy", 0.0)
                accuracy_scores.append(accuracy)
            except Exception as e:
                logger.error(f"Error evaluating accuracy: {e}")
        
        return accuracy_scores
    
    def _save_evaluation_results(self, evaluation_results: EvaluationResults, name: str) -> None:
        """Save evaluation results to disk."""
        # Create a filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_evaluation_{timestamp}.json"
        file_path = os.path.join(self.output_dir, filename)
        
        # Convert to dictionary
        results_dict = {
            "metrics": evaluation_results.metrics,
            "questions": evaluation_results.questions,
            "expected_answers": evaluation_results.expected_answers,
            "actual_answers": evaluation_results.actual_answers
        }
        
        # Save as JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2)
    
    def __del__(self):
        """Close the database session when the object is deleted."""
        if hasattr(self, 'db'):
            self.db.close() 