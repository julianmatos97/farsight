"""Unit tests for query processing."""

import pytest
from unittest.mock import MagicMock, patch

from farsight2.query_processing.query_analyzer import QueryAnalyzer
from farsight2.query_processing.content_retriever import ContentRetriever
from farsight2.query_processing.response_generator import ResponseGenerator


def test_query_analyzer_extract_companies():
    """Test extracting companies from a query."""
    # Create a QueryAnalyzer instance
    analyzer = QueryAnalyzer(api_key="test-key")
    
    # Test with a simple query
    companies = analyzer._extract_companies("What was Apple's revenue in 2023?")
    assert "Apple" in companies
    
    # Test with a ticker
    companies = analyzer._extract_companies("What was AAPL's revenue in 2023?")
    assert "AAPL" in companies


def test_query_analyzer_extract_years():
    """Test extracting years from a query."""
    # Create a QueryAnalyzer instance
    analyzer = QueryAnalyzer(api_key="test-key")
    
    # Test with a query containing a year
    years = analyzer._extract_years("What was Apple's revenue in 2023?")
    assert 2023 in years
    
    # Test with multiple years
    years = analyzer._extract_years("Compare revenue between 2022 and 2023")
    assert 2022 in years
    assert 2023 in years


@patch('farsight2.query_processing.content_retriever.UnifiedEmbeddingService')
def test_content_retriever(mock_embedding_service, repository):
    """Test retrieving content."""
    # Mock the embedding service
    mock_service = MagicMock()
    mock_service.search.return_value = [
        MagicMock(
            chunk=MagicMock(
                chunk_id="CHUNK1",
                content="Relevant content",
                content_type="text"
            ),
            relevance_score=0.95
        )
    ]
    mock_embedding_service.return_value = mock_service
    
    # Create a retriever with the repository
    retriever = ContentRetriever(repository=repository)
    retriever.embedding_service = mock_service
    
    # Mock any repository methods needed
    with patch.object(repository, 'get_document_by_id', return_value=MagicMock(document_id="DOC123")):
        # Call the method under test
        result = retriever.retrieve_content("Test query", [MagicMock(document_id="DOC123")])
        
        # Verify the result
        assert len(result) == 1
        assert result[0].relevance_score == 0.95


@patch('farsight2.query_processing.response_generator.OpenAI')
def test_response_generator(mock_openai, repository):
    """Test generating a response."""
    # Create a mock OpenAI client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="ANSWER: Test answer\n\nSOURCES:\n[1] Test source"))]
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    # Create a generator
    generator = ResponseGenerator(api_key="test-key", repository=repository)
    generator.client = mock_client
    
    # Mock the repository methods
    with patch.object(repository, 'get_document_by_id', return_value=MagicMock(
        document_id="DOC123",
        ticker="AAPL",
        year=2023,
        filing_type="10-K",
        quarter=None
    )):
        # Create mock content chunks
        content_chunks = [
            MagicMock(
                chunk_id="CHUNK1",
                document_id="DOC123",
                content="Test content",
                content_type="text",
                location="Section 1"
            )
        ]
        
        # Call the method under test
        result = generator.generate_response("Test query", content_chunks)
        
        # Verify the result
        assert hasattr(result, 'answer')
        mock_client.chat.completions.create.assert_called_once() 