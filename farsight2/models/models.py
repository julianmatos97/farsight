from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class Company(BaseModel):
    """Represents a company."""
    ticker: str = Field(..., description="Company ticker symbol")
    name: Optional[str] = Field(None, description="Company name")
    
class DocumentMetadata(BaseModel):
    """Metadata for a document."""
    document_id: str = Field(..., description="Unique document ID")
    ticker: str = Field(..., description="Company ticker symbol")
    year: int = Field(..., description="Filing year")
    quarter: Optional[int] = Field(None, description="Filing quarter (null for 10-K)")
    filing_type: Literal["10-K", "10-Q"] = Field(default=..., description="Filing type")
    filing_date: Optional[datetime] = Field(default=None, description="Filing date")
    content: Optional[str] = Field(default=None, description="Filing content")
    
class TextChunk(BaseModel):
    """A chunk of text from a document."""
    chunk_id: str = Field(..., description="Unique chunk ID")
    document_id: str = Field(..., description="ID of parent document")
    text: str = Field(..., description="Text content")
    section: Optional[str] = Field(None, description="Section in document")
    page_number: Optional[int] = Field(None, description="Page number")
    
class Table(BaseModel):
    """A table from a document."""
    chunk_id: str = Field(..., description="Unique chunk ID")
    document_id: str = Field(..., description="ID of parent document")
    table_html: str = Field(..., description="HTML representation of table")
    table_data: Optional[List[List[str]]] = Field(None, description="Structured table data")
    caption: Optional[str] = Field(None, description="Table caption")
    section: str = Field(..., description="Section in document")
    page_number: Optional[int] = Field(None, description="Page number")
    
class Chart(BaseModel):
    """A chart or figure from a document."""
    chunk_id: str = Field(..., description="Unique chunk ID")
    document_id: str = Field(..., description="ID of parent document")
    chart_data: Optional[dict] = Field(None, description="Chart data")
    caption: Optional[str] = Field(None, description="Chart caption")
    section: str = Field(..., description="Section in document")
    page_number: Optional[int] = Field(None, description="Page number")
    
class ParsedDocument(BaseModel):
    """A parsed document with its extracted content."""
    document_id: str
    metadata: DocumentMetadata
    text_chunks: List[TextChunk]
    tables: List[Table]
    charts: List[Chart]
    
class DocumentChunk(BaseModel):
    """A chunk of a document for embedding and retrieval."""
    chunk_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique chunk ID")
    document_id: str = Field(..., description="ID of parent document")
    content: str = Field(..., description="Chunk content")
    content_type: str = Field(..., description="Content type (text, table, chart)")  
    location: str = Field(..., description="Reference to the location in the document")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

class EmbeddedChunk(BaseModel):
    """A document chunk with its embedding."""
    chunk: DocumentChunk = Field(..., description="Document chunk")
    embedding: List[float] = Field(..., description="Vector embedding")
    
class QueryAnalysis(BaseModel):
    """Analysis of a query."""
    companies: List[str] = Field(default_factory=list, description="Companies mentioned")
    years: List[int] = Field(default_factory=list, description="Years mentioned")
    quarters: List[int] = Field(default_factory=list, description="Quarters mentioned")
    topics: List[str] = Field(default_factory=list, description="Topics mentioned")
    
class DocumentReference(BaseModel):
    """Reference to a document."""
    document_id: str = Field(..., description="ID of the document")
    relevance_score: float = Field(..., description="Relevance score")
    
class RelevantChunk(BaseModel):
    """A chunk of a document that is relevant to a query."""
    chunk: DocumentChunk = Field(..., description="Document chunk")
    relevance_score: float = Field(..., description="Relevance score")

class Citation(BaseModel):
    """A citation for a source used in a response."""
    document_id: str
    filing_type: str
    company: str
    year: int
    quarter: Optional[int]
    location: str
    content: str
    
class FormattedResponse:
    """A formatted response with citations."""
    response: str
    citations: List[Citation]
    
class TestSuite(BaseModel):
    """Test suite for evaluation."""
    name: Optional[str] = Field(None, description="Test suite name")
    questions: List[str] = Field(default_factory=list, description="Test questions")
    expected_answers: List[str] = Field(default_factory=list, description="Expected answers")

class EvaluationResults(BaseModel):
    """Results of an evaluation."""
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Evaluation metrics")
    questions: List[str] = Field(default_factory=list, description="Questions")
    expected_answers: List[str] = Field(default_factory=list, description="Expected answers")
    actual_answers: List[str] = Field(default_factory=list, description="Actual answers")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

class EvaluationResult(BaseModel):
    """Evaluation result."""
    test_suite_name: str = Field(..., description="Test suite name")
    name: str = Field(..., description="Evaluation name")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Evaluation metrics")
    answers: List[str] = Field(default_factory=list, description="Actual answers")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

# API Request/Response Models

class ProcessingRequest(BaseModel):
    """Request to process a 10-K or 10-Q filing."""
    ticker: str = Field(..., description="Company ticker symbol")
    year: int = Field(..., description="Filing year")
    quarter: Optional[int] = Field(None, description="Filing quarter (null for 10-K)")
    filing_type: str = Field(..., description="Filing type (10-K or 10-Q)")

class QueryRequest(BaseModel):
    """Request to query the system."""
    query: str = Field(..., description="Natural language query")

class QueryResponse(BaseModel):
    """Response to a query."""
    answer: str = Field(..., description="Answer to the query")
    citations: List[Citation] = Field(default_factory=list, description="Citations")
    documents_used: List[str] = Field(default_factory=list, description="IDs of documents used")

# Internal Models

class Document(BaseModel):
    """Document metadata."""
    document_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique document ID")
    ticker: str = Field(..., description="Company ticker")
    name: Optional[str] = Field(None, description="Company name")
    year: int = Field(..., description="Filing year")
    quarter: Optional[int] = Field(None, description="Filing quarter (null for 10-K)")
    filing_type: str = Field(..., description="Filing type (10-K or 10-Q)")
    filing_date: Optional[datetime] = Field(None, description="Filing date")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

class ContentChunk(BaseModel):
    """Chunk of document content."""
    chunk_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique chunk ID")
    document_id: str = Field(..., description="ID of parent document")
    content: str = Field(..., description="Chunk content")
    content_type: str = Field(..., description="Content type (text, table, chart)")
    location: str = Field(..., description="Location in document")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

class TestSuite(BaseModel):
    """Test suite for evaluation."""
    name: Optional[str] = Field(None, description="Test suite name")
    questions: List[str] = Field(default_factory=list, description="Test questions")
    expected_answers: List[str] = Field(default_factory=list, description="Expected answers")

class EvaluationResult(BaseModel):
    """Evaluation result."""
    test_suite_name: str = Field(..., description="Test suite name")
    name: str = Field(..., description="Evaluation name")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Evaluation metrics")
    answers: List[str] = Field(default_factory=list, description="Actual answers")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")