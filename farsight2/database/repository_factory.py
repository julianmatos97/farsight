"""Factory for creating repository instances."""

from typing import Any, Dict, Union

from farsight2.database.db import get_db_session
from farsight2.database.repository import (
    CompanyRepository,
    DocumentRepository,
    ChunkRepository,
    EmbeddingRepository,
    FactRepository,
    TextChunkRepository,
    TableRepository,
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
    def create_fact_repository():
        """Create a fact repository."""
        session = get_db_session()
        return FactRepository(session)

    @staticmethod
    def create_all_repositories() -> Dict[
        str,
        Union[
            CompanyRepository,
            DocumentRepository,
            ChunkRepository,
            EmbeddingRepository,
            TextChunkRepository,
            TableRepository,
            FactRepository,
        ],
    ]:
        """Create all repositories."""
        session = get_db_session()
        return {
            "company": CompanyRepository(session),
            "document": DocumentRepository(session),
            "chunk": ChunkRepository(session),
            "embedding": EmbeddingRepository(session),
            "text_chunk": TextChunkRepository(session),
            "table": TableRepository(session),
            "fact": FactRepository(session),
        }
