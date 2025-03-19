# These are internal models for the API.
# They are used to convert the database models to a format that can be used by the API.
# They are not used in the database.

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
    table_data: Optional[List[List[str]]] = Field(
        None, description="Structured table data"
    )
    caption: Optional[str] = Field(None, description="Table caption")
    section: str = Field(..., description="Section in document")
    page_number: Optional[int] = Field(None, description="Page number")


class ParsedDocument(BaseModel):
    """A parsed document with its extracted content."""

    document_id: str
    metadata: DocumentMetadata
    text_chunks: List[TextChunk]
    tables: List[Table]


class DocumentChunk(BaseModel):
    """A chunk of a document for embedding and retrieval."""

    chunk_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique chunk ID"
    )
    document_id: str = Field(..., description="ID of parent document")
    content: str = Field(..., description="Chunk content")
    content_type: str = Field(..., description="Content type (text, table, chart)")
    location: str = Field(..., description="Reference to the location in the document")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )


class EmbeddedChunk(BaseModel):
    """A document chunk with its embedding."""

    chunk: DocumentChunk = Field(..., description="Document chunk")
    embedding: List[float] = Field(..., description="Vector embedding")


class QueryAnalysis(BaseModel):
    """Analysis of a query."""

    query: str = Field(..., description="Query text")
    companies: List[str] = Field(
        default_factory=list, description="Companies mentioned"
    )
    years: List[int] = Field(default_factory=list, description="Years mentioned")
    quarters: List[int] = Field(default_factory=list, description="Quarters mentioned")
    topics: List[str] = Field(default_factory=list, description="Topics mentioned")
    requires_numerical_data: bool = Field(
        False, description="Whether the query requires numerical data"
    )
    data_types: List[str] = Field(
        default_factory=list,
        description="Types of data needed (e.g., text, table, chart, xbrl_fact)",
    )
    time_range: Optional[Dict[str, Any]] = Field(
        None, description="Time range for the query"
    )
    embedding: Optional[List[float]] = Field(None, description="Embedding of the query")


class DocumentReference(BaseModel):
    """Reference to a document."""

    document_id: str = Field(..., description="ID of the document")
    relevance_score: float = Field(..., description="Relevance score")


class RelevantChunk(BaseModel):
    """A chunk of a document that is relevant to a query."""

    chunk: DocumentChunk = Field(..., description="Document chunk")
    relevance_score: float = Field(..., description="Relevance score")


class Citation(BaseModel):
    """Citation for a piece of information."""

    document_id: str = Field(..., description="Document ID")
    filing_type: str = Field(..., description="Filing type")
    company: str = Field(..., description="Company name or ticker")
    year: int = Field(..., description="Filing year")
    quarter: Optional[int] = Field(None, description="Filing quarter")
    location: str = Field(..., description="Location in the document")
    content: str = Field(..., description="Cited content")
    content_type: str = Field(
        ..., description="Type of content (text, table, chart, xbrl_fact)"
    )
    fact_id: Optional[str] = Field(
        None, description="ID of the XBRL fact if applicable"
    )


class FormattedResponse(BaseModel):
    """Formatted response with citations."""

    response: str = Field(..., description="Response text")
    citations: List[Citation] = Field(default_factory=list, description="Citations")


class TestSuite(BaseModel):
    """Test suite for evaluation."""

    name: Optional[str] = Field(None, description="Test suite name")
    questions: List[str] = Field(default_factory=list, description="Test questions")
    expected_answers: List[str] = Field(
        default_factory=list, description="Expected answers"
    )


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

    response: str = Field(..., description="Answer to the query")
    citations: List[Citation] = Field(default_factory=list, description="Citations")
    documents_used: List[str] = Field(
        default_factory=list, description="IDs of documents used"
    )
    facts_used: List[Any] = Field(default_factory=list, description="Fact values used")


# Internal Models


class Document(BaseModel):
    """Document metadata."""

    document_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique document ID"
    )
    ticker: str = Field(..., description="Company ticker")
    name: Optional[str] = Field(None, description="Company name")
    year: int = Field(..., description="Filing year")
    quarter: Optional[int] = Field(None, description="Filing quarter (null for 10-K)")
    filing_type: str = Field(..., description="Filing type (10-K or 10-Q)")
    filing_date: Optional[datetime] = Field(None, description="Filing date")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )


class ContentChunk(BaseModel):
    """Chunk of document content."""

    chunk_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique chunk ID"
    )
    document_id: str = Field(..., description="ID of parent document")
    content: str = Field(..., description="Chunk content")
    content_type: str = Field(..., description="Content type (text, table, chart)")
    location: str = Field(..., description="Location in document")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )


class Fact(BaseModel):
    """
    Fact model representing a financial metric definition from XBRL data.

    Facts are standardized financial metrics defined in taxonomies like US-GAAP.
    Examples include "Revenue", "NetIncome", "Assets", etc.
    """

    fact_id: str = Field(
        ..., description="Unique fact ID (usually taxonomy + concept name)"
    )
    label: str = Field(
        "No label available", description="Human-readable label for the fact"
    )
    description: str = Field(
        "No description available", description="Detailed description of the fact"
    )
    taxonomy: str = Field(
        "us-gaap", description="Taxonomy namespace (us-gaap, dei, etc.)"
    )
    fact_type: str = Field(
        "monetary", description="Type of fact (monetary, string, date, etc.)"
    )
    period_type: Optional[str] = Field(
        None, description="Period type (instant or duration)"
    )
    embedding: Optional[List[float]] = Field(
        None, description="Vector embedding of the fact's label and description"
    )


class FactValue(BaseModel):
    """
    Fact value model representing a specific value for a fact at a point in time.

    FactValues are the actual data points in financial reports, such as:
    - Revenue for Q1 2023: $10.5 million
    - Total Assets as of Dec 31, 2023: $150 million
    """

    # Core fields
    fact_id: Optional[str] = Field(None, description="ID of the associated fact")
    ticker: Optional[str] = Field(None, description="Company ticker symbol")
    value: Optional[float] = Field(None, description="Numeric value of the fact")

    # Document reference
    document_id: Optional[str] = Field(
        None, description="ID of the filing document containing this value"
    )
    filing_type: Optional[str] = Field(
        None, description="Filing type (10-K, 10-Q, etc.)"
    )
    accession_number: Optional[str] = Field(None, description="SEC accession number")

    # Time context
    start_date: Optional[str] = Field(
        None, description="Start date of period (for duration facts)"
    )
    end_date: Optional[str] = Field(
        None, description="End date of period (for all facts)"
    )
    fiscal_year: Optional[int] = Field(None, description="Fiscal year")
    fiscal_period: Optional[str] = Field(
        None, description="Fiscal period (Q1, Q2, Q3, Q4, FY)"
    )

    # Additional context
    unit: Optional[str] = Field(
        "USD", description="Unit of measurement (USD, shares, etc.)"
    )
    decimals: Optional[int] = Field(None, description="Decimal precision")

    # Derived metrics
    year_over_year_change: Optional[float] = Field(
        None, description="YoY percentage change"
    )
    quarter_over_quarter_change: Optional[float] = Field(
        None, description="QoQ percentage change"
    )
    form: Optional[str] = Field("", description="Form (10-K, 10-Q, etc.)")


class XBRLContext(BaseModel):
    """
    XBRL context model representing the context of a fact value.

    This includes information about the time period, scenario, and entity
    that the fact value applies to.
    """

    context_id: str = Field(..., description="Context ID from XBRL")
    entity_id: str = Field(..., description="Entity CIK")
    period_start: Optional[datetime] = Field(None, description="Period start date")
    period_end: datetime = Field(..., description="Period end date")
    instant: Optional[datetime] = Field(
        None, description="Point-in-time date for instant facts"
    )
    scenario: Optional[str] = Field(
        None, description="Scenario information (actual, forecast, etc.)"
    )
    segment: Optional[Dict[str, Any]] = Field(
        None, description="Segment information (business segment, etc.)"
    )


class XBRLUnit(BaseModel):
    """
    XBRL unit model representing the unit of measurement for a fact value.

    Examples include USD, shares, etc.
    """

    unit_id: str = Field(..., description="Unit ID from XBRL")
    measure: str = Field(..., description="Unit measure (e.g., 'iso4217:USD')")
    divide_numerator: Optional[str] = Field(
        None, description="Numerator for division units"
    )
    divide_denominator: Optional[str] = Field(
        None, description="Denominator for division units"
    )


class XBRLFact(BaseModel):
    """XBRL fact model."""

    fact_id: str = Field(..., description="Unique identifier for the fact")
    concept: str = Field(..., description="XBRL concept name")
    value: str = Field(..., description="Fact value")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    context_ref: str = Field(..., description="Context reference")
    fiscal_year: int = Field(..., description="Fiscal year")
    fiscal_period: str = Field(..., description="Fiscal period (e.g., FY, Q1, Q2, Q3)")
    document_id: str = Field(..., description="ID of the document containing this fact")


class XBRLFactValue(BaseModel):
    """XBRL fact value model."""

    fact_id: str = Field(..., description="ID of the fact")
    value: str = Field(..., description="Value of the fact")
    fiscal_year: int = Field(..., description="Fiscal year")
    fiscal_period: str = Field(..., description="Fiscal period")
    document_id: str = Field(
        ..., description="ID of the document containing this value"
    )
    unit: Optional[str] = Field(None, description="Unit of measurement")
    decimals: Optional[int] = Field(None, description="Number of decimal places")
    is_rounded: bool = Field(False, description="Whether the value is rounded")
