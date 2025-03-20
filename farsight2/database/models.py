# These are the database models for the Farsight2 Postgres database.
# They are used to create the database schema and to define the relationships between the tables.
# They are not used in the API.

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.orm.relationships import _RelationshipDeclared
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector


from farsight2.database.db import Base


class Company(Base):
    """Company model."""

    __tablename__ = "companies"

    ticker = Column(String, primary_key=True)
    name = Column(String)

    documents = relationship("Document", back_populates="company")

    def __repr__(self) -> str:
        return f"<Company(ticker='{self.ticker}', name='{self.name}')>"


class Document(Base):
    """Document model."""

    __tablename__ = "documents"

    document_id = Column(String, primary_key=True)
    ticker = Column(String, ForeignKey("companies.ticker"))
    year = Column(Integer)
    quarter = Column(Integer, nullable=True)
    filing_type = Column(String)
    filing_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    company = relationship("Company", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")
    text_chunks = relationship("TextChunkDB", back_populates="document")
    tables = relationship("TableDB", back_populates="document")

    def __repr__(self) -> str:
        return f"<Document(document_id='{self.document_id}', ticker='{self.ticker}', year={self.year}, quarter={self.quarter}, filing_type='{self.filing_type}')>"


class DocumentChunk(Base):
    """Document chunk model."""

    __tablename__ = "document_chunks"

    chunk_id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.document_id"))
    content = Column(Text)
    content_type = Column(String)
    location = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    document = relationship("Document", back_populates="chunks")
    embedding = relationship("ChunkEmbedding", back_populates="chunk", uselist=False)

    def __repr__(self) -> str:
        return f"<DocumentChunk(chunk_id='{self.chunk_id}', document_id='{self.document_id}', content_type='{self.content_type}')>"


class ChunkEmbedding(Base):
    """Chunk embedding model."""

    __tablename__ = "chunk_embeddings"

    id = Column(Integer, primary_key=True)
    chunk_id = Column(String, ForeignKey("document_chunks.chunk_id"))
    embedding = Column(
        Vector(3072)
    )  # Using pgvector's Vector type with OpenAI's embedding dimension
    created_at = Column(DateTime, server_default=func.now())

    chunk = relationship("DocumentChunk", back_populates="embedding")

    def __repr__(self) -> str:
        return f"<ChunkEmbedding(id={self.id}, chunk_id='{self.chunk_id}')>"


class TextChunkDB(Base):
    """Text chunk model."""

    __tablename__ = "text_chunks"

    chunk_id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.document_id"))
    text = Column(Text)
    section = Column(String)
    page_number = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    document = relationship("Document", back_populates="text_chunks")

    def __repr__(self) -> str:
        return f"<TextChunkDB(chunk_id='{self.chunk_id}', document_id='{self.document_id}', section='{self.section}')>"


class TableDB(Base):
    """Table model."""

    __tablename__ = "tables"

    chunk_id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.document_id"))
    table_html = Column(Text)
    table_data = Column(JSON)
    caption = Column(String)
    section = Column(String)
    page_number = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    document = relationship("Document", back_populates="tables")

    def __repr__(self) -> str:
        return f"<TableDB(chunk_id='{self.chunk_id}', document_id='{self.document_id}', section='{self.section}')>"


class Fact(Base):
    """Fact model representing a financial metric definition from XBRL data."""

    __tablename__ = "facts"

    fact_id = Column(String, primary_key=True)
    label = Column(String, default="No label available")
    description = Column(String, default="No description available")
    taxonomy = Column(String, default="us-gaap")
    fact_type = Column(String, default="monetary")
    period_type = Column(String, nullable=True)
    embedding = Column(
        Vector(3072)
    )  # Using pgvector's Vector type with OpenAI's embedding dimension
    fact_values = relationship("FactValue", back_populates="fact")

    def __repr__(self) -> str:
        return f"<Fact(fact_id='{self.fact_id}', label='{self.label}')>"


class FactValue(Base):
    """Fact value model."""

    __tablename__ = "fact_values"
    id = Column(Integer, primary_key=True)
    fact_id = Column(String, ForeignKey("facts.fact_id"))
    ticker = Column(String, nullable=True)
    value = Column(Float, nullable=True)
    document_id = Column(String, nullable=True)
    filing_type = Column(String, nullable=True)
    accession_number = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    fiscal_year = Column(Integer, nullable=True)
    fiscal_period = Column(Integer, nullable=True)
    unit = Column(String, default="USD")
    decimals = Column(Integer, nullable=True)
    year_over_year_change = Column(Float, nullable=True)
    quarter_over_quarter_change = Column(Float, nullable=True)
    form = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    fact = relationship("Fact", back_populates="fact_values")

    def __repr__(self) -> str:
        return f"<FactValue(value={self.value}, fact_id='{self.fact_id}', document_id='{self.document_id}', fiscal_year={self.fiscal_year}, fiscal_period='{self.fiscal_period}')>"
