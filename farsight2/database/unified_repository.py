"""Unified repository class that combines all repositories."""

from typing import List, Dict, Any, Optional
import logging

from farsight2.models.models import (
    Company as CompanyModel,
    DocumentMetadata,
    DocumentChunk as DocumentChunkModel,
    EmbeddedChunk,
    RelevantChunk,
    TestSuite as TestSuiteModel,
    EvaluationResults as EvaluationResultsModel,
    TextChunk as TextChunkModel,
    Table as TableModel,
    Chart as ChartModel
)
from farsight2.database.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)

class UnifiedRepository:
    """Unified repository class that combines all repositories."""
    
    def __init__(self):
        """Initialize the repository."""
        self._repos = RepositoryFactory.create_all_repositories()
    
    # Company methods
    
    def create_company(self, ticker: str, name: Optional[str] = None) -> CompanyModel:
        """Create a company."""
        company = self._repos['company'].create_company(ticker, name)
        return self._repos['company'].to_model(company)
    
    def get_company(self, ticker: str) -> Optional[CompanyModel]:
        """Get a company by ticker."""
        company = self._repos['company'].get_company(ticker)
        return self._repos['company'].to_model(company) if company else None
    
    def get_all_companies(self) -> List[CompanyModel]:
        """Get all companies."""
        companies = self._repos['company'].get_all_companies()
        return [self._repos['company'].to_model(company) for company in companies]
    
    # Document methods
    
    def create_document(self, document: DocumentMetadata) -> DocumentMetadata:
        """Create a document."""
        doc = self._repos['document'].create_document(document)
        return self._repos['document'].to_model(doc)
    
    def get_document(self, ticker: str, year: int, quarter: Optional[int], filing_type: str) -> Optional[DocumentMetadata]:
        """Get a document by criteria."""
        docs = self._repos['document'].get_documents_by_ticker_year_and_quarter(ticker, year, quarter)
        for doc in docs:
            if doc.filing_type == filing_type:
                return self._repos['document'].to_model(doc)
        return None
    
    def get_document_by_id(self, document_id: str) -> Optional[DocumentMetadata]:
        """Get a document by ID."""
        doc = self._repos['document'].get_document(document_id)
        return self._repos['document'].to_model(doc) if doc else None
    
    def get_documents_by_company(self, ticker: str) -> List[DocumentMetadata]:
        """Get documents by company."""
        docs = self._repos['document'].get_documents_by_ticker(ticker)
        return [self._repos['document'].to_model(doc) for doc in docs]
    
    def get_all_documents(self, limit: int = 100) -> List[DocumentMetadata]:
        """Get all documents."""
        docs = self._repos['document'].get_all_documents()
        return [self._repos['document'].to_model(doc) for doc in docs[:limit]]
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document."""
        doc = self._repos['document'].get_document(document_id)
        if not doc:
            return False
        
        # Delete all related entities
        try:
            # Delete chunks and embeddings
            chunks = self._repos['chunk'].get_chunks_by_document(document_id)
            for chunk in chunks:
                embedding = self._repos['embedding'].get_embedding(chunk.chunk_id)
                if embedding:
                    self._repos['embedding'].db.delete(embedding)
                self._repos['chunk'].db.delete(chunk)
            
            # Delete text chunks
            text_chunks = self._repos['text_chunk'].get_text_chunks_by_document(document_id)
            for chunk in text_chunks:
                self._repos['text_chunk'].db.delete(chunk)
            
            # Delete tables
            tables = self._repos['table'].get_tables_by_document(document_id)
            for table in tables:
                self._repos['table'].db.delete(table)
            
            # Delete charts
            charts = self._repos['chart'].get_charts_by_document(document_id)
            for chart in charts:
                self._repos['chart'].db.delete(chart)
            
            # Delete document
            self._repos['document'].db.delete(doc)
            self._repos['document'].db.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            self._repos['document'].db.rollback()
            return False
    
    # Content chunk methods
    
    def create_content_chunk(self, chunk: DocumentChunkModel, embedding: List[float] = None) -> DocumentChunkModel:
        """Create a content chunk."""
        db_chunk = self._repos['chunk'].create_chunk(chunk)
        
        # If embedding is provided, create embedding record
        if embedding:
            embedded_chunk = EmbeddedChunk(chunk=chunk, embedding=embedding)
            self._repos['embedding'].create_embedding(embedded_chunk)
        
        return self._repos['chunk'].to_model(db_chunk)
    
    def get_content_chunk(self, chunk_id: str) -> Optional[DocumentChunkModel]:
        """Get a content chunk by ID."""
        chunk = self._repos['chunk'].get_chunk(chunk_id)
        return self._repos['chunk'].to_model(chunk) if chunk else None
    
    def get_content_chunks_by_document(self, document_id: str) -> List[DocumentChunkModel]:
        """Get content chunks by document."""
        chunks = self._repos['chunk'].get_chunks_by_document(document_id)
        return [self._repos['chunk'].to_model(chunk) for chunk in chunks]
    
    # Search methods
    
    def search_embeddings(self, query_embedding: List[float], top_k: int = 5,
                         filter_dict: Optional[Dict[str, Any]] = None) -> List[RelevantChunk]:
        """Search for relevant chunks."""
        results = self._repos['embedding'].search_embeddings(query_embedding, top_k, filter_dict)
        relevant_chunks = []
        
        for chunk, score in results:
            chunk_model = self._repos['chunk'].to_model(chunk)
            relevant_chunks.append(RelevantChunk(chunk=chunk_model, relevance_score=score))
        
        return relevant_chunks
    
    # Text chunk methods
    
    def create_text_chunk(self, text_chunk: TextChunkModel) -> TextChunkModel:
        """Create a text chunk."""
        db_chunk = self._repos['text_chunk'].create_text_chunk(text_chunk)
        return self._repos['text_chunk'].to_model(db_chunk)
    
    def get_text_chunk(self, chunk_id: str) -> Optional[TextChunkModel]:
        """Get a text chunk by ID."""
        chunk = self._repos['text_chunk'].get_text_chunk(chunk_id)
        return self._repos['text_chunk'].to_model(chunk) if chunk else None
    
    # Table methods
    
    def create_table(self, table: TableModel) -> TableModel:
        """Create a table."""
        db_table = self._repos['table'].create_table(table)
        return self._repos['table'].to_model(db_table)
    
    def get_table(self, chunk_id: str) -> Optional[TableModel]:
        """Get a table by ID."""
        table = self._repos['table'].get_table(chunk_id)
        return self._repos['table'].to_model(table) if table else None
    
    # Chart methods
    
    def create_chart(self, chart: ChartModel) -> ChartModel:
        """Create a chart."""
        db_chart = self._repos['chart'].create_chart(chart)
        return self._repos['chart'].to_model(db_chart)
    
    def get_chart(self, chunk_id: str) -> Optional[ChartModel]:
        """Get a chart by ID."""
        chart = self._repos['chart'].get_chart(chunk_id)
        return self._repos['chart'].to_model(chart) if chart else None
    
    # Test suite methods
    
    def create_test_suite(self, name: str, questions: List[str], expected_answers: List[str]) -> TestSuiteModel:
        """Create a test suite."""
        test_suite = self._repos['test_suite'].create_test_suite(name, questions, expected_answers)
        return self._repos['test_suite'].to_model(test_suite)
    
    def get_test_suite(self, name: str) -> Optional[TestSuiteModel]:
        """Get a test suite by name."""
        test_suite = self._repos['test_suite'].get_test_suite(name)
        return self._repos['test_suite'].to_model(test_suite) if test_suite else None
    
    # Evaluation methods
    
    def create_evaluation(self, test_suite_name: str, name: str, metrics: Dict[str, Any],
                         questions: List[str], expected_answers: List[str], actual_answers: List[str]) -> EvaluationResultsModel:
        """Create an evaluation."""
        evaluation = self._repos['evaluation'].create_evaluation(
            test_suite_name, name, metrics, questions, expected_answers, actual_answers
        )
        return self._repos['evaluation'].to_model(evaluation)
    
    def get_evaluation(self, name: str) -> Optional[EvaluationResultsModel]:
        """Get an evaluation by name."""
        evaluation = self._repos['evaluation'].get_evaluation(name)
        return self._repos['evaluation'].to_model(evaluation) if evaluation else None 