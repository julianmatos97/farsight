"""Unit tests for evaluation components."""

import pytest
from unittest.mock import MagicMock, patch

from farsight2.evaluation.test_suite import Evaluator


@patch('farsight2.evaluation.test_suite.OpenAI')
def test_evaluator_run_test_suite(mock_openai, repository):
    """Test running a test suite."""
    # Mock OpenAI client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="4"))]  # Score of 4 out of 5
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    # Create an evaluator
    evaluator = Evaluator(api_key="test-key", repository=repository)
    evaluator.client = mock_client
    
    # Mock repository methods
    with patch.object(repository, 'get_test_suite', return_value=MagicMock(
        id=1,
        name="Test Suite",
        questions=[
            MagicMock(id=1, question="Question 1?", expected_answer="Expected Answer 1"),
            MagicMock(id=2, question="Question 2?", expected_answer="Expected Answer 2")
        ]
    )):
        with patch.object(repository, 'create_evaluation_result', return_value=MagicMock(
            id=1,
            test_suite_id=1,
            name="Test Evaluation"
        )):
            with patch.object(repository, 'create_evaluation_answer', return_value=MagicMock()):
                with patch.object(evaluator, '_generate_answer', return_value="Generated Answer"):
                    with patch.object(evaluator, '_evaluate_answer', return_value=4):
                        # Call the method under test
                        result = evaluator.run_test_suite("Test Suite", "Test Evaluation")
                        
                        # Verify the result
                        assert result is not None
                        assert result.metrics["average_score"] > 0
                        assert len(result.answers) > 0 