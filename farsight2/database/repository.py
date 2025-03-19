"""Repository module for database operations."""

from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, text

from farsight2.constants import generate_document_id
from farsight2.database.models import (
    Company,
    Document,
    DocumentChunk,
    ChunkEmbedding,
    Fact,
    FactValue,
    TextChunkDB,
    TableDB,
)
from farsight2.embedding.unified_embedding_service import UnifiedEmbeddingService
from farsight2.models.models import (
    Company as CompanyModel,
    DocumentMetadata,
    DocumentChunk as DocumentChunkModel,
    EmbeddedChunk,
    Fact as FactModel,
    FactValue as FactValueModel,
    TestSuite as TestSuiteModel,
    EvaluationResults as EvaluationResultsModel,
    TextChunk as TextChunkModel,
    Table as TableModel,
    Chart as ChartModel,
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
        return CompanyModel(ticker=company.ticker, name=company.name or "")


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

        if document := self.get_document(document_metadata.document_id):
            return document
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
            filing_date=document_metadata.filing_date,
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
        return (
            self.db.query(Document).filter(Document.document_id == document_id).first()
        )

    def get_documents_by_ticker(self, ticker: str) -> List[Document]:
        """Get documents by ticker.

        Args:
            ticker: Company ticker

        Returns:
            List of documents
        """
        return self.db.query(Document).filter(Document.ticker == ticker).all()

    def get_documents_by_ticker_and_year(
        self, ticker: str, year: int
    ) -> List[Document]:
        """Get documents by ticker and year.

        Args:
            ticker: Company ticker
            year: Filing year

        Returns:
            List of documents
        """
        return (
            self.db.query(Document)
            .filter(Document.ticker == ticker, Document.year == year)
            .all()
        )

    def get_documents_by_ticker_year_and_quarter(
        self, ticker: str, year: int, quarter: Optional[int]
    ) -> List[Document]:
        """Get documents by ticker, year, and quarter.

        Args:
            ticker: Company ticker
            year: Filing year
            quarter: Filing quarter

        Returns:
            List of documents
        """
        query = self.db.query(Document).filter(
            Document.ticker == ticker, Document.year == year
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
            filing_date=document.filing_date,
        )

    def get_document_registry(self) -> Dict[str, List[DocumentMetadata]]:
        """Get the document registry.

        Returns:
            Dictionary mapping company tickers to lists of document metadata
        """
        documents = self.get_all_documents()
        registry = {}
        # TODO - why are we loading this all into memory?
        for document in documents:
            if document.ticker not in registry:
                registry[document.ticker] = []

            registry[document.ticker].append(self.to_model(document))
        print(f"Document registry: {registry}")
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
                "filing_date": document.filing_date.isoformat()
                if document.filing_date
                else None,
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
            location=chunk.location,
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
        return (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.chunk_id == chunk_id)
            .first()
        )

    def get_chunks_by_document(self, document_id: str) -> List[DocumentChunk]:
        """Get document chunks by document ID.

        Args:
            document_id: Document ID

        Returns:
            List of document chunks
        """
        return (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .all()
        )

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
            location=chunk.location,
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
            chunk_id=chunk.chunk_id, embedding=embedded_chunk.embedding
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
        return (
            self.db.query(ChunkEmbedding)
            .filter(ChunkEmbedding.chunk_id == chunk_id)
            .first()
        )

    def search_embeddings(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """Search for the most similar chunks to a query embedding.

        Args:
            query_embedding: Query embedding
            top_k: Number of results to return
            filter_dict: Dictionary of filters to apply

        Returns:
            List of tuples containing document chunks and their similarity scores
        """
        # Convert query embedding to array for pgvector
        query_vector = query_embedding

        # Start with a base query using pgvector's cosine_distance
        query = self.db.query(
            DocumentChunk,
            (1 - ChunkEmbedding.embedding.cosine_distance(query_vector)).label(
                "similarity"
            ),  # Convert distance to similarity
        ).join(ChunkEmbedding, DocumentChunk.chunk_id == ChunkEmbedding.chunk_id)

        # Apply filters if provided
        if filter_dict:
            if "document_id" in filter_dict:
                query = query.filter(
                    DocumentChunk.document_id == filter_dict["document_id"]
                )
            if "content_type" in filter_dict:
                query = query.filter(
                    DocumentChunk.content_type == filter_dict["content_type"]
                )

        # Order by similarity (descending) and limit to top_k
        results = query.order_by(text("similarity DESC")).limit(top_k).all()

        # Convert to list of tuples
        return [(chunk, float(similarity)) for chunk, similarity in results]

    def to_model(
        self, chunk: DocumentChunk, embedding: ChunkEmbedding
    ) -> EmbeddedChunk:
        """Convert a document chunk and embedding entities to a model.

        Args:
            chunk: Document chunk entity
            embedding: Chunk embedding entity

        Returns:
            Embedded chunk model
        """
        chunk_repo = ChunkRepository(self.db)
        return EmbeddedChunk(
            chunk=chunk_repo.to_model(chunk), embedding=embedding.embedding
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
            text=" ".join(text_chunk.text.split()),
            section=text_chunk.section,
            page_number=text_chunk.page_number,
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
        return (
            self.db.query(TextChunkDB).filter(TextChunkDB.chunk_id == chunk_id).first()
        )

    def get_text_chunks_by_document(self, document_id: str) -> List[TextChunkDB]:
        """Get text chunks by document ID.

        Args:
            document_id: Document ID

        Returns:
            List of text chunks
        """
        return (
            self.db.query(TextChunkDB)
            .filter(TextChunkDB.document_id == document_id)
            .all()
        )

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
            page_number=text_chunk.page_number,
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
            page_number=table.page_number,
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
            page_number=table.page_number,
        )


class FactRepository:
    """Repository for fact operations."""

    def __init__(self, db: Session):
        """Initialize the repository.

        Args:
            db: Database session
        """
        self.db = db
        self.embedding_service = UnifiedEmbeddingService()

    def create_fact(self, fact: FactModel) -> Fact:
        """Create a fact.

        Args:
            fact: Fact model

        Returns:
            Created fact
        """
        if not fact.embedding:
            fact.embedding = self.embedding_service.embed_fact(fact)
        db_fact = Fact(
            fact_id=fact.fact_id,
            label=fact.label,
            description=fact.description,
            taxonomy=fact.taxonomy,
            fact_type=fact.fact_type,
            period_type=fact.period_type,
            embedding=fact.embedding if fact.embedding else None,
        )
        self.db.add(db_fact)
        self.db.commit()
        self.db.refresh(db_fact)
        return db_fact

    def get_fact(self, fact_id: str) -> Optional[Fact]:
        """Get a fact by ID.

        Args:
            fact_id: Fact ID

        Returns:
            Fact if found, None otherwise
        """
        return self.db.query(Fact).filter(Fact.fact_id == fact_id).first()

    def get_all_facts(self) -> List[Fact]:
        """Get all facts.

        Returns:
            List of facts
        """
        return self.db.query(Fact).all()

    def fact_to_model(self, fact: Fact) -> FactModel:
        """Convert a fact entity to a model.

        Args:
            fact: Fact entity

        Returns:
            Fact model
        """
        return FactModel(
            fact_id=fact.fact_id,
            label=fact.label,
            description=fact.description,
            taxonomy=fact.taxonomy,
            fact_type=fact.fact_type,
            period_type=fact.period_type,
        )

    def create_fact_value(self, fact_value: FactValueModel) -> FactValue:
        """Create a fact value.

        Args:
            fact_value: Fact value model

        Returns:
            Created fact value
        """
        db_fact_value = FactValue(
            fact_id=fact_value.fact_id,
            ticker=fact_value.ticker,
            value=fact_value.value,
            document_id=fact_value.document_id,
            filing_type=fact_value.filing_type,
            accession_number=fact_value.accession_number,
            start_date=fact_value.start_date,
            end_date=fact_value.end_date,
            fiscal_year=fact_value.fiscal_year,
            fiscal_period=fact_value.fiscal_period,
            unit=fact_value.unit,
            decimals=fact_value.decimals,
            year_over_year_change=fact_value.year_over_year_change,
            quarter_over_quarter_change=fact_value.quarter_over_quarter_change,
            form=fact_value.form,
        )
        self.db.add(db_fact_value)
        self.db.commit()
        self.db.refresh(db_fact_value)
        return db_fact_value

    def get_fact_value(self, fact_value_id: str) -> Optional[FactValue]:
        """Get a fact value by ID.

        Args:
            fact_value_id: Fact value ID

        Returns:
            Fact value if found, None otherwise
        """
        return (
            self.db.query(FactValue)
            .filter(FactValue.fact_value_id == fact_value_id)
            .first()
        )

    def get_all_fact_values(self) -> List[FactValue]:
        """Get all fact values.

        Returns:
            List of fact values
        """
        return self.db.query(FactValue).all()

    def fact_value_to_model(self, fact_value: FactValue) -> FactValueModel:
        """Convert a fact value entity to a model.

        Args:
            fact_value: Fact value entity

        Returns:
            Fact value model
        """
        return FactValueModel(
            fact_id=fact_value.fact_id,
            ticker=fact_value.ticker,
            value=fact_value.value,
            document_id=fact_value.document_id,
            filing_type=fact_value.filing_type,
            accession_number=fact_value.accession_number,
            start_date=fact_value.start_date,
            end_date=fact_value.end_date,
            fiscal_year=fact_value.fiscal_year,
            fiscal_period=fact_value.fiscal_period,
            unit=fact_value.unit,
            decimals=fact_value.decimals,
            year_over_year_change=fact_value.year_over_year_change,
            quarter_over_quarter_change=fact_value.quarter_over_quarter_change,
            form=fact_value.form,
        )

    def get_fact_values_by_fact(self, fact_id: str) -> List[FactValue]:
        """Get all fact values for a fact.

        Args:
            fact_id: Fact ID

        Returns:
            List of fact values
        """
        return self.db.query(FactValue).filter(FactValue.fact_id == fact_id).all()

    def get_fact_value_by_details(
        self,
        fact_id: str,
        ticker: str,
        year: int,
        quarter: Optional[int],
        filing_type: str,
    ) -> Optional[FactValue]:
        """Get a fact value by its details.

        Args:
            fact_id: Fact ID
            document_id: Document ID
            fiscal_year: Fiscal year
            fiscal_period: Fiscal period

        Returns:
            Fact value if found, None otherwise

        """
        document_id = generate_document_id(ticker, year, quarter, filing_type)
        return (
            self.db.query(FactValue)
            .filter(
                FactValue.fact_id == fact_id,
                FactValue.document_id == document_id,
            )
            .first()
        )

    def search_facts_by_embedding(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[Fact]:
        """
        Search for facts using vector similarity.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return

        Returns:
            List of tuples containing (fact, similarity_score)
        """
        # Convert query embedding to array
        query_vector = query_embedding

        # Use cosine similarity with pgvector
        results = (
            self.db.query(
                Fact, Fact.embedding.cosine_distance(query_vector).label("distance")
            )
            .filter(Fact.embedding != None)
            .order_by("distance")
            .limit(top_k)
            .all()
        )

        print(f"Results: {results}")
        # Convert distance to similarity score (cosine distance = 1 - cosine similarity)
        return [fact for fact, _ in results]

    def search_facts_by_text(
        self, query: str, embedding_service, top_k: int = 5
    ) -> List[Tuple[Fact, float]]:
        """
        Search for facts using text query.

        Args:
            query: Text query
            embedding_service: Service to generate embeddings
            top_k: Number of results to return

        Returns:
            List of tuples containing (fact, similarity_score)
        """
        # Generate embedding for the query
        query_embedding = embedding_service.generate_embedding(query)
        return self.search_facts_by_embedding(query_embedding, top_k)

    def get_facts_values_by_company_and_year(
        self, ticker: str, year: int
    ) -> List[FactValue]:
        """Get all facts values for a company and year.

        Args:
            ticker: Company ticker
            year: Fiscal year

        Returns:
            List of fact values
        """
        return (
            self.db.query(FactValue)
            .filter(FactValue.ticker == ticker, FactValue.fiscal_year == year)
            .all()
        )
