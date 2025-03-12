"""Unit tests for embedding services."""

import pytest
from unittest.mock import MagicMock, patch

from farsight2.embedding.unified_embedding_service import UnifiedEmbeddingService


def test_generate_embedding(embedding_service):
    """Test generating an embedding."""
    # Call the method under test
    result = embedding_service.generate_embedding("Test text")
    
    # Verify the result
    assert len(result) == 1536
    embedding_service.client.embeddings.create.assert_called_once()


def test_search(embedding_service, repository):
    """Test searching for relevant content."""
    # Fix: Use patch to mock repository search
    with patch.object(repository, 'search_embeddings', return_value=[
        MagicMock(
            chunk=MagicMock(
                chunk_id="CHUNK1",
                content="Relevant content",
                content_type="text"
            ),
            relevance_score=0.95
        )
    ]):
        # Call the method under test
        result = embedding_service.search("Test query")
        
        # Verify the result
        assert len(result) == 1
        assert result[0].relevance_score == 0.95
        embedding_service.client.embeddings.create.assert_called_once()


def test_embedding_document(embedding_service, repository):
    """Test embedding a document."""
    # Create a mock document
    mock_document = MagicMock(
        document_id="DOC123",
        text_chunks=[
            MagicMock(
                chunk_id="CHUNK1",
                document_id="DOC123",
                text="Test text",
                section="Section 1"
            )
        ],
        tables=[],
        charts=[]
    )
    
    # Fix: Use patch to mock repository methods
    with patch.object(repository, 'create_content_chunk', return_value=MagicMock()):
        with patch.object(repository, 'create_embedding', return_value=MagicMock()):
            # Call the method under test
            result = embedding_service.embed_document(mock_document)
            
            # Verify the result
            assert len(result) == 1
            assert result[0].chunk.document_id == "DOC123"
            embedding_service.client.embeddings.create.assert_called_once() 