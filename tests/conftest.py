"""Common fixtures for Farsight2 tests."""

import os
import pytest
import tempfile
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from farsight2.database.db import Base
from farsight2.database.models import (
    Company, Document, DocumentChunk, ChunkEmbedding,
    TextChunkDB, TableDB, ChartDB
)
from farsight2.database.unified_repository import UnifiedRepository
from farsight2.embedding.unified_embedding_service import UnifiedEmbeddingService
from farsight2.models.models import DocumentMetadata


@pytest.fixture(scope="session")
def test_db_url():
    """Create a test database URL."""
    # Use SQLite for testing to avoid PostgreSQL dependency
    return "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine(test_db_url):
    """Create a test database engine."""
    engine = create_engine(test_db_url)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a test database session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def repository(db_session):
    """Create a repository instance with a test database session."""
    repo = UnifiedRepository()
    # Replace the database session with our test session
    repo._repos = {
        'company': MagicMock(db=db_session),
        'document': MagicMock(db=db_session),
        'chunk': MagicMock(db=db_session),
        'embedding': MagicMock(db=db_session),
        'text_chunk': MagicMock(db=db_session),
        'table': MagicMock(db=db_session),
        'chart': MagicMock(db=db_session),
        'test_suite': MagicMock(db=db_session),
        'evaluation': MagicMock(db=db_session),
    }
    return repo


@pytest.fixture(scope="function")
def mock_openai():
    """Mock OpenAI API client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
    mock_client.embeddings.create.return_value = mock_response
    
    # Mock chat completions
    mock_chat_response = MagicMock()
    mock_chat_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
    mock_client.chat.completions.create.return_value = mock_chat_response
    
    return mock_client


@pytest.fixture(scope="function")
def embedding_service(repository, mock_openai):
    """Create an embedding service with mocked OpenAI client."""
    service = UnifiedEmbeddingService(api_key="test-key", repository=repository)
    service.client = mock_openai
    return service


@pytest.fixture(scope="function")
def sample_document():
    """Create a sample document for testing."""
    return DocumentMetadata(
        document_id="DOC123",
        ticker="AAPL",
        year=2023,
        quarter=None,
        filing_type="10-K",
        filing_date="2023-12-31"
    )


@pytest.fixture(scope="function")
def temp_file():
    """Create a temporary file for testing."""
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(b"Test content for document processing")
    temp.close()
    yield temp.name
    os.unlink(temp.name) 