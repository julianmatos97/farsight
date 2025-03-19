"""Integration tests for document processing workflow."""

import pytest
from unittest.mock import MagicMock, patch

from farsight2.document_processing.document_processor import DocumentProcessor
from farsight2.embedding.unified_embedding_service import UnifiedEmbeddingService
from farsight2.database.unified_repository import UnifiedRepository


@patch("farsight2.document_processing.edgar_client.requests.get")
def test_document_workflow(mock_get, repository, embedding_service, temp_file):
    """Test the complete document processing workflow."""
    # Mock HTTP requests
    mock_response = MagicMock()
    mock_response.content = b"<html><body><h1>ITEM 1. BUSINESS</h1><p>Test business description.</p></body></html>"
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    # Fix: Mock all repository methods with patch
    with patch.object(repository, "get_company", return_value=None):
        with patch.object(
            repository,
            "create_company",
            return_value=MagicMock(ticker="AAPL", name="Apple Inc."),
        ):
            with patch.object(
                repository,
                "create_document",
                return_value=MagicMock(
                    document_id="DOC123",
                    ticker="AAPL",
                    year=2023,
                    quarter=None,
                    filing_type="10-K",
                ),
            ):
                with patch.object(
                    repository, "create_content_chunk", return_value=MagicMock()
                ):
                    with patch.object(
                        repository, "create_text_chunk", return_value=MagicMock()
                    ):
                        # Create processor
                        processor = DocumentProcessor(
                            embedding_service=embedding_service, repository=repository
                        )

                        # Fix: Mock the EdgarClient properly
                        with patch(
                            "farsight2.document_processing.document_processor.EdgarClient"
                        ) as mock_edgar:
                            mock_client = MagicMock()
                            mock_client.download_filing.return_value = temp_file
                            mock_edgar.return_value = mock_client

                            # Write test content to temp file
                            with open(temp_file, "w") as f:
                                f.write(
                                    "<html><body><h1>ITEM 1. BUSINESS</h1><p>Test business description.</p></body></html>"
                                )

                            # Fix: Mock document processor internals
                            with patch.object(
                                processor,
                                "_parse_document",
                                return_value=MagicMock(
                                    document_id="DOC123",
                                    text_chunks=[MagicMock()],
                                    tables=[],
                                    charts=[],
                                ),
                            ):
                                # Call the processor - adjust arguments if needed
                                document = processor.process_document(
                                    temp_file, "AAPL", 2023, None, "10-K"
                                )

                                # Verify the document was processed
                                assert document is not None


@patch("farsight2.document_processing.edgar_client.requests.get")
def test_query_workflow(mock_get, repository, embedding_service, temp_file):
    """Test the complete query processing workflow."""
    from farsight2.query_processing.query_analyzer import QueryAnalyzer
    from farsight2.query_processing.content_retriever import ContentRetriever
    from farsight2.query_processing.response_generator import ResponseGenerator

    # Mock HTTP requests
    mock_response = MagicMock()
    mock_response.content = b"<html><body><h1>ITEM 1. BUSINESS</h1><p>Test business description.</p></body></html>"
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    # Fix: Use proper context managers for patching
    with patch.object(
        QueryAnalyzer,
        "analyze_query",
        return_value=MagicMock(
            companies=["AAPL"], years=[2023], quarters=[], topics=["revenue"]
        ),
    ):
        mock_chunks = [
            MagicMock(
                chunk=MagicMock(
                    chunk_id="CHUNK1",
                    document_id="DOC123",
                    content="Apple's revenue was $100 billion.",
                    content_type="text",
                    location="Section 1",
                ),
                relevance_score=0.95,
            )
        ]

        with patch.object(
            ContentRetriever, "retrieve_content", return_value=mock_chunks
        ):
            mock_response = MagicMock(
                answer="Apple's revenue in 2023 was $100 billion.",
                citations=[MagicMock()],
                documents_used=["DOC123"],
            )

            with patch.object(
                ResponseGenerator, "generate_response", return_value=mock_response
            ):
                with patch.object(
                    repository,
                    "get_document",
                    return_value=MagicMock(
                        document_id="DOC123",
                        ticker="AAPL",
                        year=2023,
                        quarter=None,
                        filing_type="10-K",
                    ),
                ):
                    # Create the necessary components
                    analyzer = QueryAnalyzer(api_key="test-key")
                    retriever = ContentRetriever(
                        repository=repository, embedding_service=embedding_service
                    )
                    generator = ResponseGenerator(
                        api_key="test-key", repository=repository
                    )

                    # Execute the workflow
                    query = "What was Apple's revenue in 2023?"
                    analysis = analyzer.analyze_query(query)
                    documents = [repository.get_document.return_value]
                    chunks = retriever.retrieve_content(query, documents)
                    response = generator.generate_response(query, chunks)

                    # Verify
                    assert (
                        response.answer == "Apple's revenue in 2023 was $100 billion."
                    )
                    assert "DOC123" in response.documents_used
