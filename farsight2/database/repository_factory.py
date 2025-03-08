"""Factory for creating repository instances."""

from typing import Any, Dict

from farsight2.database.db import get_db_session
from farsight2.database.repository import (
    CompanyRepository,
    DocumentRepository,
    ChunkRepository,
    EmbeddingRepository,
    TestSuiteRepository,
    EvaluationRepository,
    TextChunkRepository,
    TableRepository,
    ChartRepository
)

class RepositoryFactory:
    """Factory for creating repository instances."""
    
    @staticmethod
    def create_company_repository():
        """Create a company repository."""
        session = get_db_session()
        return CompanyRepository(session)
    
    @staticmethod
    def create_document_repository():
        """Create a document repository."""
        session = get_db_session()
        return DocumentRepository(session)
    
    @staticmethod
    def create_chunk_repository():
        """Create a chunk repository."""
        session = get_db_session()
        return ChunkRepository(session)
    
    @staticmethod
    def create_embedding_repository():
        """Create an embedding repository."""
        session = get_db_session()
        return EmbeddingRepository(session)
    
    @staticmethod
    def create_test_suite_repository():
        """Create a test suite repository."""
        session = get_db_session()
        return TestSuiteRepository(session)
    
    @staticmethod
    def create_evaluation_repository():
        """Create an evaluation repository."""
        session = get_db_session()
        return EvaluationRepository(session)
    
    @staticmethod
    def create_text_chunk_repository():
        """Create a text chunk repository."""
        session = get_db_session()
        return TextChunkRepository(session)
    
    @staticmethod
    def create_table_repository():
        """Create a table repository."""
        session = get_db_session()
        return TableRepository(session)
    
    @staticmethod
    def create_chart_repository():
        """Create a chart repository."""
        session = get_db_session()
        return ChartRepository(session)
    
    @staticmethod
    def create_all_repositories() -> Dict[str, Any]:
        """Create all repositories."""
        session = get_db_session()
        return {
            'company': CompanyRepository(session),
            'document': DocumentRepository(session),
            'chunk': ChunkRepository(session),
            'embedding': EmbeddingRepository(session),
            'test_suite': TestSuiteRepository(session),
            'evaluation': EvaluationRepository(session),
            'text_chunk': TextChunkRepository(session),
            'table': TableRepository(session),
            'chart': ChartRepository(session)
        } 