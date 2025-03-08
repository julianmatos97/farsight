"""Database models for Farsight2."""


from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


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
    charts = relationship("ChartDB", back_populates="document")
    
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
    embedding = Column("embedding", String)  # This will be converted to vector type in SQL
    created_at = Column(DateTime, server_default=func.now())
    
    chunk = relationship("DocumentChunk", back_populates="embedding")
    
    def __repr__(self) -> str:
        return f"<ChunkEmbedding(id={self.id}, chunk_id='{self.chunk_id}')>"

class TestSuite(Base):
    """Test suite model."""
    
    __tablename__ = "test_suites"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    created_at = Column(DateTime, server_default=func.now())
    
    questions = relationship("TestQuestion", back_populates="test_suite")
    evaluation_results = relationship("EvaluationResult", back_populates="test_suite")
    
    def __repr__(self) -> str:
        return f"<TestSuite(id={self.id}, name='{self.name}')>"

class TestQuestion(Base):
    """Test question model."""
    
    __tablename__ = "test_questions"
    
    id = Column(Integer, primary_key=True)
    test_suite_id = Column(Integer, ForeignKey("test_suites.id"))
    question = Column(Text)
    expected_answer = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    test_suite = relationship("TestSuite", back_populates="questions")
    evaluation_answers = relationship("EvaluationAnswer", back_populates="question")
    
    def __repr__(self) -> str:
        return f"<TestQuestion(id={self.id}, test_suite_id={self.test_suite_id}, question='{self.question[:50]}...')>"

class EvaluationResult(Base):
    """Evaluation result model."""
    
    __tablename__ = "evaluation_results"
    
    id = Column(Integer, primary_key=True)
    test_suite_id = Column(Integer, ForeignKey("test_suites.id"))
    name = Column(String)
    metrics = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    
    test_suite = relationship("TestSuite", back_populates="evaluation_results")
    answers = relationship("EvaluationAnswer", back_populates="evaluation")
    
    def __repr__(self) -> str:
        return f"<EvaluationResult(id={self.id}, test_suite_id={self.test_suite_id}, name='{self.name}')>"

class EvaluationAnswer(Base):
    """Evaluation answer model."""
    
    __tablename__ = "evaluation_answers"
    
    id = Column(Integer, primary_key=True)
    evaluation_id = Column(Integer, ForeignKey("evaluation_results.id"))
    question_id = Column(Integer, ForeignKey("test_questions.id"))
    actual_answer = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    evaluation = relationship("EvaluationResult", back_populates="answers")
    question = relationship("TestQuestion", back_populates="evaluation_answers")
    
    def __repr__(self) -> str:
        return f"<EvaluationAnswer(id={self.id}, evaluation_id={self.evaluation_id}, question_id={self.question_id})>"

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

class ChartDB(Base):
    """Chart model."""
    
    __tablename__ = "charts"
    
    chunk_id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.document_id"))
    chart_data = Column(JSON)
    caption = Column(String)
    section = Column(String)
    page_number = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    
    document = relationship("Document", back_populates="charts")
    
    def __repr__(self) -> str:
        return f"<ChartDB(chunk_id='{self.chunk_id}', document_id='{self.document_id}', section='{self.section}')>" 