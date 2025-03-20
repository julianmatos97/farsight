"""Unified repository class that combines all repositories."""

from typing import List, Dict, Any, Optional, Tuple
import logging
import numpy as np

from farsight2.models.models import (
    Company as CompanyModel,
    DocumentMetadata,
    DocumentChunk as DocumentChunkModel,
    EmbeddedChunk,
    Fact,
    FactValue,
    RelevantChunk,
    TextChunk as TextChunkModel,
    Table as TableModel,
)
from farsight2.database.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)


class UnifiedRepository:
    """Unified repository class that combines all repositories for the Postgres database."""

    def __init__(self):
        """Initialize the repository."""
        self._repos = RepositoryFactory.create_all_repositories()

    # Company methods

    def create_company(self, ticker: str, name: Optional[str] = None) -> CompanyModel:
        """Create a company."""
        company = self._repos["company"].create_company(ticker, name)
        return self._repos["company"].to_model(company)

    def get_company(self, ticker: str) -> Optional[CompanyModel]:
        """Get a company by ticker."""
        company = self._repos["company"].get_company(ticker)
        return self._repos["company"].to_model(company) if company else None

    def get_all_companies(self) -> List[CompanyModel]:
        """Get all companies."""
        companies = self._repos["company"].get_all_companies()
        return [self._repos["company"].to_model(company) for company in companies]

    # Document methods

    def create_document(self, document: DocumentMetadata) -> DocumentMetadata:
        """Create a document."""
        doc = self._repos["document"].create_document(document)
        return self._repos["document"].to_model(doc)

    def get_document(
        self, ticker: str, year: int, quarter: Optional[int], filing_type: str
    ) -> Optional[DocumentMetadata]:
        """Get a document by criteria."""
        docs = self._repos["document"].get_documents_by_ticker_year_and_quarter(
            ticker, year, quarter
        )
        for doc in docs:
            if doc.filing_type == filing_type:
                return self._repos["document"].to_model(doc)
        return None

    def get_document_by_id(self, document_id: str) -> Optional[DocumentMetadata]:
        """Get a document by ID."""
        doc = self._repos["document"].get_document(document_id)
        return self._repos["document"].to_model(doc) if doc else None

    def get_documents_by_company(self, ticker: str) -> List[DocumentMetadata]:
        """Get documents by company."""
        docs = self._repos["document"].get_documents_by_ticker(ticker)
        return [self._repos["document"].to_model(doc) for doc in docs]

    def get_all_documents(self, limit: int = 100) -> List[DocumentMetadata]:
        """Get all documents."""
        docs = self._repos["document"].get_all_documents()
        return [self._repos["document"].to_model(doc) for doc in docs[:limit]]

    def delete_document(self, document_id: str) -> bool:
        """Delete a document."""
        doc = self._repos["document"].get_document(document_id)
        if not doc:
            return False

        # Delete all related entities
        try:
            # Delete chunks and embeddings
            chunks = self._repos["chunk"].get_chunks_by_document(document_id)
            for chunk in chunks:
                embedding = self._repos["embedding"].get_embedding(chunk.chunk_id)
                if embedding:
                    self._repos["embedding"].db.delete(embedding)
                self._repos["chunk"].db.delete(chunk)

            # Delete text chunks
            text_chunks = self._repos["text_chunk"].get_text_chunks_by_document(
                document_id
            )
            for chunk in text_chunks:
                self._repos["text_chunk"].db.delete(chunk)

            # Delete tables
            tables = self._repos["table"].get_tables_by_document(document_id)
            for table in tables:
                self._repos["table"].db.delete(table)

            # Delete document
            self._repos["document"].db.delete(doc)
            self._repos["document"].db.commit()

            return True
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            self._repos["document"].db.rollback()
            return False

    # Content chunk methods

    def create_content_chunk(
        self, chunk: DocumentChunkModel, embedding: List[float] = None
    ) -> DocumentChunkModel:
        """Create a content chunk."""
        db_chunk = self._repos["chunk"].create_chunk(chunk)

        # If embedding is provided, create embedding record
        if embedding:
            embedded_chunk = EmbeddedChunk(chunk=chunk, embedding=embedding)
            self._repos["embedding"].create_embedding(embedded_chunk)

        return self._repos["chunk"].to_model(db_chunk)

    def get_content_chunk(self, chunk_id: str) -> Optional[DocumentChunkModel]:
        """Get a content chunk by ID."""
        chunk = self._repos["chunk"].get_chunk(chunk_id)
        return self._repos["chunk"].to_model(chunk) if chunk else None

    def get_content_chunks_by_document(
        self, document_id: str
    ) -> List[DocumentChunkModel]:
        """Get content chunks by document."""
        chunks = self._repos["chunk"].get_chunks_by_document(document_id)
        return [self._repos["chunk"].to_model(chunk) for chunk in chunks]

    # Search methods

    def search_embeddings(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[RelevantChunk]:
        """Search for relevant chunks."""
        results = self._repos["embedding"].search_embeddings(
            query_embedding, top_k, filter_dict
        )
        relevant_chunks = []

        for chunk, score in results:
            chunk_model = self._repos["chunk"].to_model(chunk)
            relevant_chunks.append(
                RelevantChunk(chunk=chunk_model, relevance_score=score)
            )

        return relevant_chunks

    # Text chunk methods

    def create_text_chunk(self, text_chunk: TextChunkModel) -> TextChunkModel:
        """Create a text chunk."""
        db_chunk = self._repos["text_chunk"].create_text_chunk(text_chunk)
        return self._repos["text_chunk"].to_model(db_chunk)

    def get_text_chunk(self, chunk_id: str) -> Optional[TextChunkModel]:
        """Get a text chunk by ID."""
        chunk = self._repos["text_chunk"].get_text_chunk(chunk_id)
        return self._repos["text_chunk"].to_model(chunk) if chunk else None

    # Table methods

    def create_table(self, table: TableModel) -> TableModel:
        """Create a table."""
        db_table = self._repos["table"].create_table(table)
        return self._repos["table"].to_model(db_table)

    def get_table(self, chunk_id: str) -> Optional[TableModel]:
        """Get a table by ID."""
        table = self._repos["table"].get_table(chunk_id)
        return self._repos["table"].to_model(table) if table else None

    def create_fact(self, fact: Fact) -> Fact:
        """
        Create a fact definition in the database.

        Args:
            fact: Fact model with definition information

        Returns:
            The created fact
        """
        try:
            db_fact = self._repos["fact"].create_fact(fact)
            return self._repos["fact"].fact_to_model(db_fact)
        except Exception:
            return None

    def get_fact(self, fact_id: str) -> Optional[Fact]:
        """
        Get a fact by ID.

        Args:
            fact_id: Unique fact identifier

        Returns:
            Fact if found, None otherwise
        """
        db_fact = self._repos["fact"].get_fact(fact_id)
        return self._repos["fact"].fact_to_model(db_fact) if db_fact else None

    def get_all_facts(self) -> List[Fact]:
        """
        Get all facts.

        Returns:
            List of all facts in the database
        """
        facts = self._repos["fact"].get_all_facts()
        return [self._repos["fact"].fact_to_model(fact) for fact in facts]

    def update_fact(self, fact: Fact) -> Fact:
        """Update a fact."""
        db_fact = self._repos["fact"].update_fact(fact)
        return self._repos["fact"].fact_to_model(db_fact)

    def get_facts_by_taxonomy(self, taxonomy: str) -> List[Fact]:
        """
        Get facts by taxonomy.

        Args:
            taxonomy: Taxonomy name (e.g., 'us-gaap', 'dei')

        Returns:
            List of facts belonging to the specified taxonomy
        """
        facts = self._repos["fact"].get_facts_by_taxonomy(taxonomy)
        return [self._repos["fact"].fact_to_model(fact) for fact in facts]

    def get_primary_facts(self) -> List[Fact]:
        """
        Get primary financial metrics.

        Returns:
            List of facts marked as primary financial metrics
        """
        facts = self._repos["fact"].get_primary_facts()
        return [self._repos["fact"].fact_to_model(fact) for fact in facts]

    def create_fact_value(self, fact_value: FactValue) -> FactValue:
        """
        Create a fact value in the database.

        Args:
            fact_value: FactValue model with the actual data point

        Returns:
            The created fact value
        """
        db_fact_value = self._repos["fact"].create_fact_value(fact_value)
        return self._repos["fact"].fact_value_to_model(db_fact_value)

    def get_fact_value(self, fact_value_id: str) -> Optional[FactValue]:
        """
        Get a fact value by ID.

        Args:
            fact_value_id: Unique fact value identifier

        Returns:
            FactValue if found, None otherwise
        """
        db_fact_value = self._repos["fact"].get_fact_value(fact_value_id)
        return (
            self._repos["fact"].fact_value_to_model(db_fact_value)
            if db_fact_value
            else None
        )

    def get_fact_value_by_details(
        self,
        fact_id: str,
        ticker: str,
        year: int,
        quarter: Optional[int],
        filing_type: str,
    ) -> Optional[FactValue]:
        """
        Get a fact value by its details.

        Args:
            fact_id: Fact identifier
            document_id: Document identifier
            fiscal_year: Fiscal year
            fiscal_period: Fiscal period (e.g., 'Q1', 'FY')

        Returns:
            FactValue if found, None otherwise
        """
        db_fact_value = self._repos["fact"].get_fact_value_by_details(
            fact_id, ticker, year, quarter, filing_type
        )
        return (
            self._repos["fact"].fact_value_to_model(db_fact_value)
            if db_fact_value
            else None
        )

    def get_fact_values_by_details(
        self,
        fact_id: str,
        ticker: str,
        year: int,
        quarter: Optional[int],
        filing_type: str,
    ) -> List[FactValue]:
        """Get a fact value by its details.

        Args:
            fact_id: Fact ID
            ticker: Company ticker
            year: Fiscal year
            quarter: Fiscal period
            filing_type: Filing type

        Returns:
            List of fact values for the specified details
        """
        db_fact_values = self._repos["fact"].get_fact_values_by_details(
            fact_id, ticker, year, quarter, filing_type
        )
        return [self._repos["fact"].fact_value_to_model(fv) for fv in db_fact_values]

    def get_fact_values_by_ticker(self, ticker: str) -> List[FactValue]:
        """
        Get all fact values for a company.

        Args:
            ticker: Company ticker symbol

        Returns:
            List of fact values for the company
        """
        fact_values = self._repos["fact"].get_fact_values_by_ticker(ticker)
        return [self._repos["fact"].fact_value_to_model(fv) for fv in fact_values]

    def get_fact_values_by_document(self, document_id: str) -> List[FactValue]:
        """
        Get all fact values for a document.

        Args:
            document_id: Document identifier

        Returns:
            List of fact values associated with the document
        """
        fact_values = self._repos["fact"].get_fact_values_by_document(document_id)
        return [self._repos["fact"].fact_value_to_model(fv) for fv in fact_values]

    def get_fact_values_by_fact(
        self, fact_id: str, ticker: str = None, limit: int = 20
    ) -> List[FactValue]:
        """
        Get values for a specific fact, optionally filtered by company.

        Args:
            fact_id: Fact identifier
            ticker: Optional company ticker to filter by
            limit: Maximum number of values to return

        Returns:
            List of fact values for the specified fact
        """
        fact_values = self._repos["fact"].get_fact_values_by_fact(
            fact_id, ticker, limit
        )
        return [self._repos["fact"].fact_value_to_model(fv) for fv in fact_values]

    def search_facts_by_query(
        self, query: str, top_k: int = 5
    ) -> List[Tuple[Fact, float]]:
        """
        Search for facts using semantic similarity to a query.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of tuples containing (fact, similarity_score)
        """
        try:
            # Get all facts with embeddings
            facts = self.get_all_facts()
            facts_with_embeddings = [f for f in facts if f.embedding is not None]

            if not facts_with_embeddings:
                logger.warning("No facts with embeddings found")
                return []

            # Get embeddings list
            embeddings = [f.embedding for f in facts_with_embeddings]

            # Search using fact embedder
            top_indices = self.fact_embedder.search_facts(query, embeddings, top_k)

            # Get similarities for the top results
            query_embedding = self.fact_embedder.model.encode(query)
            similarities = [
                float(
                    np.dot(facts_with_embeddings[i].embedding, query_embedding)
                    / (
                        np.linalg.norm(facts_with_embeddings[i].embedding)
                        * np.linalg.norm(query_embedding)
                    )
                )
                for i in top_indices
            ]

            # Return facts with their similarity scores
            return [
                (facts_with_embeddings[i], similarities[j])
                for j, i in enumerate(top_indices)
            ]
        except Exception as e:
            logger.error(f"Error searching facts: {str(e)}")
            return []
