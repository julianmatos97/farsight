"""Repository module for database operations."""

from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from farsight2.database.models import (
    Company,
    Document,
    DocumentChunk,
    ChunkEmbedding,
    TestSuite,
    TestQuestion,
    EvaluationResult,
    EvaluationAnswer,
    TextChunkDB,
    TableDB,
    ChartDB
)
from farsight2.models.models import (
    Company as CompanyModel,
    DocumentMetadata,
    DocumentChunk as DocumentChunkModel,
    EmbeddedChunk,
    TestSuite as TestSuiteModel,
    EvaluationResults as EvaluationResultsModel,
    TextChunk as TextChunkModel,
    Table as TableModel,
    Chart as ChartModel
)

class CompanyRepository:
    """Repository for company operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_company(self, ticker: str, name: Optional[str] = None) -> Company:
        """Create a company.
        
        Args:
            ticker: Company ticker
            name: Company name
            
        Returns:
            Created company
        """
        company = Company(ticker=ticker, name=name)
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company
    
    def get_company(self, ticker: str) -> Optional[Company]:
        """Get a company by ticker.
        
        Args:
            ticker: Company ticker
            
        Returns:
            Company if found, None otherwise
        """
        return self.db.query(Company).filter(Company.ticker == ticker).first()
    
    def get_or_create_company(self, ticker: str, name: Optional[str] = None) -> Company:
        """Get a company by ticker or create it if it doesn't exist.
        
        Args:
            ticker: Company ticker
            name: Company name
            
        Returns:
            Company
        """
        company = self.get_company(ticker)
        if not company:
            company = self.create_company(ticker, name)
        return company
    
    def get_all_companies(self) -> List[Company]:
        """Get all companies.
        
        Returns:
            List of companies
        """
        return self.db.query(Company).all()
    
    def to_model(self, company: Company) -> CompanyModel:
        """Convert a company entity to a model.
        
        Args:
            company: Company entity
            
        Returns:
            Company model
        """
        return CompanyModel(
            ticker=company.ticker,
            name=company.name or ""
        )

class DocumentRepository:
    """Repository for document operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_document(self, document_metadata: DocumentMetadata) -> Document:
        """Create a document.
        
        Args:
            document_metadata: Document metadata
            
        Returns:
            Created document
        """
        # Ensure the company exists
        company_repo = CompanyRepository(self.db)
        company_repo.get_or_create_company(document_metadata.ticker)
        
        # Create the document
        document = Document(
            document_id=document_metadata.document_id,
            ticker=document_metadata.ticker,
            year=document_metadata.year,
            quarter=document_metadata.quarter,
            filing_type=document_metadata.filing_type,
            filing_date=document_metadata.filing_date
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document if found, None otherwise
        """
        return self.db.query(Document).filter(Document.document_id == document_id).first()
    
    def get_documents_by_ticker(self, ticker: str) -> List[Document]:
        """Get documents by ticker.
        
        Args:
            ticker: Company ticker
            
        Returns:
            List of documents
        """
        return self.db.query(Document).filter(Document.ticker == ticker).all()
    
    def get_documents_by_ticker_and_year(self, ticker: str, year: int) -> List[Document]:
        """Get documents by ticker and year.
        
        Args:
            ticker: Company ticker
            year: Filing year
            
        Returns:
            List of documents
        """
        return self.db.query(Document).filter(
            Document.ticker == ticker,
            Document.year == year
        ).all()
    
    def get_documents_by_ticker_year_and_quarter(self, ticker: str, year: int, quarter: Optional[int]) -> List[Document]:
        """Get documents by ticker, year, and quarter.
        
        Args:
            ticker: Company ticker
            year: Filing year
            quarter: Filing quarter
            
        Returns:
            List of documents
        """
        query = self.db.query(Document).filter(
            Document.ticker == ticker,
            Document.year == year
        )
        
        if quarter is not None:
            query = query.filter(Document.quarter == quarter)
        
        return query.all()
    
    def get_all_documents(self) -> List[Document]:
        """Get all documents.
        
        Returns:
            List of documents
        """
        return self.db.query(Document).all()
    
    def to_model(self, document: Document) -> DocumentMetadata:
        """Convert a document entity to a model.
        
        Args:
            document: Document entity
            
        Returns:
            Document metadata model
        """
        return DocumentMetadata(
            document_id=document.document_id,
            ticker=document.ticker,
            year=document.year,
            quarter=document.quarter,
            filing_type=document.filing_type,
            filing_date=document.filing_date
        )
    
    def get_document_registry(self) -> Dict[str, List[DocumentMetadata]]:
        """Get the document registry.
        
        Returns:
            Dictionary mapping company tickers to lists of document metadata
        """
        documents = self.get_all_documents()
        registry = {}
        
        for document in documents:
            if document.ticker not in registry:
                registry[document.ticker] = []
            
            registry[document.ticker].append(self.to_model(document))
        
        return registry
    
    def get_document_metadata_store(self) -> Dict[str, Dict[str, Any]]:
        """Get the document metadata store.
        
        Returns:
            Dictionary mapping document IDs to metadata dictionaries
        """
        documents = self.get_all_documents()
        store = {}
        
        for document in documents:
            store[document.document_id] = {
                "ticker": document.ticker,
                "year": document.year,
                "quarter": document.quarter,
                "filing_type": document.filing_type,
                "filing_date": document.filing_date.isoformat() if document.filing_date else None
            }
        
        return store

class ChunkRepository:
    """Repository for document chunk operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_chunk(self, chunk: DocumentChunkModel) -> DocumentChunk:
        """Create a document chunk.
        
        Args:
            chunk: Document chunk model
            
        Returns:
            Created document chunk
        """
        # Ensure the document exists
        document_repo = DocumentRepository(self.db)
        document = document_repo.get_document(chunk.document_id)
        if not document:
            raise ValueError(f"Document not found: {chunk.document_id}")
        
        # Create the chunk
        db_chunk = DocumentChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            content=chunk.content,
            content_type=chunk.content_type,
            location=chunk.location
        )
        self.db.add(db_chunk)
        self.db.commit()
        self.db.refresh(db_chunk)
        return db_chunk
    
    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Get a document chunk by ID.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            Document chunk if found, None otherwise
        """
        return self.db.query(DocumentChunk).filter(DocumentChunk.chunk_id == chunk_id).first()
    
    def get_chunks_by_document(self, document_id: str) -> List[DocumentChunk]:
        """Get document chunks by document ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            List of document chunks
        """
        return self.db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
    
    def to_model(self, chunk: DocumentChunk) -> DocumentChunkModel:
        """Convert a document chunk entity to a model.
        
        Args:
            chunk: Document chunk entity
            
        Returns:
            Document chunk model
        """
        return DocumentChunkModel(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            content=chunk.content,
            content_type=chunk.content_type,
            location=chunk.location
        )

class EmbeddingRepository:
    """Repository for embedding operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_embedding(self, embedded_chunk: EmbeddedChunk) -> ChunkEmbedding:
        """Create a chunk embedding.
        
        Args:
            embedded_chunk: Embedded chunk
            
        Returns:
            Created chunk embedding
        """
        # Ensure the chunk exists
        chunk_repo = ChunkRepository(self.db)
        chunk = chunk_repo.get_chunk(embedded_chunk.chunk.chunk_id)
        if not chunk:
            # Create the chunk
            chunk = chunk_repo.create_chunk(embedded_chunk.chunk)
        
        # Create the embedding
        embedding = ChunkEmbedding(
            chunk_id=chunk.chunk_id,
            embedding=embedded_chunk.embedding
        )
        self.db.add(embedding)
        self.db.commit()
        self.db.refresh(embedding)
        return embedding
    
    def get_embedding(self, chunk_id: str) -> Optional[ChunkEmbedding]:
        """Get a chunk embedding by chunk ID.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            Chunk embedding if found, None otherwise
        """
        return self.db.query(ChunkEmbedding).filter(ChunkEmbedding.chunk_id == chunk_id).first()
    
    def search_embeddings(self, query_embedding: List[float], top_k: int = 5, 
                         filter_dict: Optional[Dict[str, Any]] = None) -> List[Tuple[DocumentChunk, float]]:
        """Search for the most similar chunks to a query embedding.
        
        Args:
            query_embedding: Query embedding
            top_k: Number of results to return
            filter_dict: Dictionary of filters to apply
            
        Returns:
            List of tuples containing document chunks and their similarity scores
        """
        # Start with a base query
        query = self.db.query(
            DocumentChunk,
            func.cosine_similarity(ChunkEmbedding.embedding, query_embedding).label("similarity")
        ).join(
            ChunkEmbedding, DocumentChunk.chunk_id == ChunkEmbedding.chunk_id
        )
        
        # Apply filters if provided
        if filter_dict:
            if "document_id" in filter_dict:
                query = query.filter(DocumentChunk.document_id == filter_dict["document_id"])
            if "content_type" in filter_dict:
                query = query.filter(DocumentChunk.content_type == filter_dict["content_type"])
        
        # Order by similarity and limit to top_k
        results = query.order_by(func.cosine_similarity(ChunkEmbedding.embedding, query_embedding).desc()).limit(top_k).all()
        
        # Convert to list of tuples
        return [(chunk, float(similarity)) for chunk, similarity in results]
    
    def to_model(self, chunk: DocumentChunk, embedding: ChunkEmbedding) -> EmbeddedChunk:
        """Convert a document chunk and embedding entities to a model.
        
        Args:
            chunk: Document chunk entity
            embedding: Chunk embedding entity
            
        Returns:
            Embedded chunk model
        """
        chunk_repo = ChunkRepository(self.db)
        return EmbeddedChunk(
            chunk=chunk_repo.to_model(chunk),
            embedding=embedding.embedding
        )

class TestSuiteRepository:
    """Repository for test suite operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_test_suite(self, name: str, questions: List[str], expected_answers: List[str]) -> TestSuite:
        """Create a test suite.
        
        Args:
            name: Test suite name
            questions: List of questions
            expected_answers: List of expected answers
            
        Returns:
            Created test suite
        """
        # Create the test suite
        test_suite = TestSuite(name=name)
        self.db.add(test_suite)
        self.db.commit()
        self.db.refresh(test_suite)
        
        # Create the questions
        for question, expected_answer in zip(questions, expected_answers):
            test_question = TestQuestion(
                test_suite_id=test_suite.id,
                question=question,
                expected_answer=expected_answer
            )
            self.db.add(test_question)
        
        self.db.commit()
        self.db.refresh(test_suite)
        return test_suite
    
    def get_test_suite(self, name: str) -> Optional[TestSuite]:
        """Get a test suite by name.
        
        Args:
            name: Test suite name
            
        Returns:
            Test suite if found, None otherwise
        """
        return self.db.query(TestSuite).filter(TestSuite.name == name).first()
    
    def get_test_suite_by_id(self, test_suite_id: int) -> Optional[TestSuite]:
        """Get a test suite by ID.
        
        Args:
            test_suite_id: Test suite ID
            
        Returns:
            Test suite if found, None otherwise
        """
        return self.db.query(TestSuite).filter(TestSuite.id == test_suite_id).first()
    
    def get_all_test_suites(self) -> List[TestSuite]:
        """Get all test suites.
        
        Returns:
            List of test suites
        """
        return self.db.query(TestSuite).all()
    
    def to_model(self, test_suite: TestSuite) -> TestSuiteModel:
        """Convert a test suite entity to a model.
        
        Args:
            test_suite: Test suite entity
            
        Returns:
            Test suite model
        """
        questions = [question.question for question in test_suite.questions]
        expected_answers = [question.expected_answer or "" for question in test_suite.questions]
        
        return TestSuiteModel(
            questions=questions,
            expected_answers=expected_answers
        )

class EvaluationRepository:
    """Repository for evaluation operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_evaluation(self, test_suite_name: str, name: str, metrics: Dict[str, Any], 
                         questions: List[str], expected_answers: List[str], actual_answers: List[str]) -> EvaluationResult:
        """Create an evaluation result.
        
        Args:
            test_suite_name: Test suite name
            name: Evaluation name
            metrics: Evaluation metrics
            questions: List of questions
            expected_answers: List of expected answers
            actual_answers: List of actual answers
            
        Returns:
            Created evaluation result
        """
        # Get the test suite
        test_suite_repo = TestSuiteRepository(self.db)
        test_suite = test_suite_repo.get_test_suite(test_suite_name)
        if not test_suite:
            raise ValueError(f"Test suite not found: {test_suite_name}")
        
        # Create the evaluation result
        evaluation_result = EvaluationResult(
            test_suite_id=test_suite.id,
            name=name,
            metrics=metrics
        )
        self.db.add(evaluation_result)
        self.db.commit()
        self.db.refresh(evaluation_result)
        
        # Create the answers
        for i, (question, actual_answer) in enumerate(zip(questions, actual_answers)):
            # Find the corresponding test question
            test_question = None
            for q in test_suite.questions:
                if q.question == question:
                    test_question = q
                    break
            
            if not test_question:
                continue
            
            # Create the evaluation answer
            evaluation_answer = EvaluationAnswer(
                evaluation_id=evaluation_result.id,
                question_id=test_question.id,
                actual_answer=actual_answer
            )
            self.db.add(evaluation_answer)
        
        self.db.commit()
        self.db.refresh(evaluation_result)
        return evaluation_result
    
    def get_evaluation(self, name: str) -> Optional[EvaluationResult]:
        """Get an evaluation result by name.
        
        Args:
            name: Evaluation name
            
        Returns:
            Evaluation result if found, None otherwise
        """
        return self.db.query(EvaluationResult).filter(EvaluationResult.name == name).first()
    
    def get_evaluation_by_id(self, evaluation_id: int) -> Optional[EvaluationResult]:
        """Get an evaluation result by ID.
        
        Args:
            evaluation_id: Evaluation ID
            
        Returns:
            Evaluation result if found, None otherwise
        """
        return self.db.query(EvaluationResult).filter(EvaluationResult.id == evaluation_id).first()
    
    def get_all_evaluations(self) -> List[EvaluationResult]:
        """Get all evaluation results.
        
        Returns:
            List of evaluation results
        """
        return self.db.query(EvaluationResult).all()
    
    def to_model(self, evaluation_result: EvaluationResult) -> EvaluationResultsModel:
        """Convert an evaluation result entity to a model.
        
        Args:
            evaluation_result: Evaluation result entity
            
        Returns:
            Evaluation results model
        """
        # Get the test suite
        test_suite = evaluation_result.test_suite
        
        # Get the questions and answers
        questions = [question.question for question in test_suite.questions]
        expected_answers = [question.expected_answer or "" for question in test_suite.questions]
        
        # Create a mapping from question ID to index
        question_id_to_index = {question.id: i for i, question in enumerate(test_suite.questions)}
        
        # Initialize actual answers with empty strings
        actual_answers = [""] * len(questions)
        
        # Fill in the actual answers
        for answer in evaluation_result.answers:
            if answer.question_id in question_id_to_index:
                index = question_id_to_index[answer.question_id]
                actual_answers[index] = answer.actual_answer
        
        return EvaluationResultsModel(
            metrics=evaluation_result.metrics,
            questions=questions,
            expected_answers=expected_answers,
            actual_answers=actual_answers
        )

class TextChunkRepository:
    """Repository for text chunk operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_text_chunk(self, text_chunk: TextChunkModel) -> TextChunkDB:
        """Create a text chunk.
        
        Args:
            text_chunk: Text chunk model
            
        Returns:
            Created text chunk
        """
        # Ensure the document exists
        document_repo = DocumentRepository(self.db)
        document = document_repo.get_document(text_chunk.document_id)
        if not document:
            raise ValueError(f"Document not found: {text_chunk.document_id}")
        
        # Create the text chunk
        db_text_chunk = TextChunkDB(
            chunk_id=text_chunk.chunk_id,
            document_id=text_chunk.document_id,
            text=text_chunk.text,
            section=text_chunk.section,
            page_number=text_chunk.page_number
        )
        self.db.add(db_text_chunk)
        self.db.commit()
        self.db.refresh(db_text_chunk)
        return db_text_chunk
    
    def get_text_chunk(self, chunk_id: str) -> Optional[TextChunkDB]:
        """Get a text chunk by ID.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            Text chunk if found, None otherwise
        """
        return self.db.query(TextChunkDB).filter(TextChunkDB.chunk_id == chunk_id).first()
    
    def get_text_chunks_by_document(self, document_id: str) -> List[TextChunkDB]:
        """Get text chunks by document ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            List of text chunks
        """
        return self.db.query(TextChunkDB).filter(TextChunkDB.document_id == document_id).all()
    
    def to_model(self, text_chunk: TextChunkDB) -> TextChunkModel:
        """Convert a text chunk entity to a model.
        
        Args:
            text_chunk: Text chunk entity
            
        Returns:
            Text chunk model
        """
        return TextChunkModel(
            chunk_id=text_chunk.chunk_id,
            document_id=text_chunk.document_id,
            text=text_chunk.text,
            section=text_chunk.section,
            page_number=text_chunk.page_number
        )

class TableRepository:
    """Repository for table operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_table(self, table: TableModel) -> TableDB:
        """Create a table.
        
        Args:
            table: Table model
            
        Returns:
            Created table
        """
        # Ensure the document exists
        document_repo = DocumentRepository(self.db)
        document = document_repo.get_document(table.document_id)
        if not document:
            raise ValueError(f"Document not found: {table.document_id}")
        
        # Create the table
        db_table = TableDB(
            chunk_id=table.chunk_id,
            document_id=table.document_id,
            table_html=table.table_html,
            table_data=table.table_data,
            caption=table.caption,
            section=table.section,
            page_number=table.page_number
        )
        self.db.add(db_table)
        self.db.commit()
        self.db.refresh(db_table)
        return db_table
    
    def get_table(self, chunk_id: str) -> Optional[TableDB]:
        """Get a table by ID.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            Table if found, None otherwise
        """
        return self.db.query(TableDB).filter(TableDB.chunk_id == chunk_id).first()
    
    def get_tables_by_document(self, document_id: str) -> List[TableDB]:
        """Get tables by document ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            List of tables
        """
        return self.db.query(TableDB).filter(TableDB.document_id == document_id).all()
    
    def to_model(self, table: TableDB) -> TableModel:
        """Convert a table entity to a model.
        
        Args:
            table: Table entity
            
        Returns:
            Table model
        """
        return TableModel(
            chunk_id=table.chunk_id,
            document_id=table.document_id,
            table_html=table.table_html,
            table_data=table.table_data,
            caption=table.caption,
            section=table.section,
            page_number=table.page_number
        )

class ChartRepository:
    """Repository for chart operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_chart(self, chart: ChartModel) -> ChartDB:
        """Create a chart.
        
        Args:
            chart: Chart model
            
        Returns:
            Created chart
        """
        # Ensure the document exists
        document_repo = DocumentRepository(self.db)
        document = document_repo.get_document(chart.document_id)
        if not document:
            raise ValueError(f"Document not found: {chart.document_id}")
        
        # Create the chart
        db_chart = ChartDB(
            chunk_id=chart.chunk_id,
            document_id=chart.document_id,
            chart_data=chart.chart_data,
            caption=chart.caption,
            section=chart.section,
            page_number=chart.page_number
        )
        self.db.add(db_chart)
        self.db.commit()
        self.db.refresh(db_chart)
        return db_chart
    
    def get_chart(self, chunk_id: str) -> Optional[ChartDB]:
        """Get a chart by ID.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            Chart if found, None otherwise
        """
        return self.db.query(ChartDB).filter(ChartDB.chunk_id == chunk_id).first()
    
    def get_charts_by_document(self, document_id: str) -> List[ChartDB]:
        """Get charts by document ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            List of charts
        """
        return self.db.query(ChartDB).filter(ChartDB.document_id == document_id).all()
    
    def to_model(self, chart: ChartDB) -> ChartModel:
        """Convert a chart entity to a model.
        
        Args:
            chart: Chart entity
            
        Returns:
            Chart model
        """
        return ChartModel(
            chunk_id=chart.chunk_id,
            document_id=chart.document_id,
            chart_data=chart.chart_data,
            caption=chart.caption,
            section=chart.section,
            page_number=chart.page_number
        ) 