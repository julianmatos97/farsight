"""FastAPI application for the Farsight2 API."""

import logging
import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from farsight2.document_processing.edgar_client import EdgarClient
from farsight2.document_processing.document_processor import DocumentProcessor
from farsight2.embedding.embedder import Embedder
from farsight2.vector_store.vector_store import VectorStore
from farsight2.query_processing.query_analyzer import QueryAnalyzer
from farsight2.query_processing.document_selector import DocumentSelector
from farsight2.query_processing.content_retriever import ContentRetriever
from farsight2.query_processing.response_generator import ResponseGenerator
from farsight2.database.db import get_db_session, init_db
from farsight2.database.repository import (
    DocumentRepository
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Farsight2 API",
    description="API for processing and querying 10-K/10-Q filings",
    version="0.1.0"
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Database initialized")

# Request and response models
class ProcessDocumentRequest(BaseModel):
    ticker: str = Field(..., description="Company ticker symbol")
    year: int = Field(..., description="Filing year")
    quarter: Optional[int] = Field(None, description="Filing quarter (for 10-Q)")
    filing_type: str = Field(..., description="Filing type (10-K or 10-Q)")

class ProcessDocumentResponse(BaseModel):
    document_id: str = Field(..., description="Document ID")
    ticker: str = Field(..., description="Company ticker symbol")
    year: int = Field(..., description="Filing year")
    quarter: Optional[int] = Field(None, description="Filing quarter (for 10-Q)")
    filing_type: str = Field(..., description="Filing type (10-K or 10-Q)")
    filing_date: str = Field(..., description="Filing date")
    status: str = Field(..., description="Processing status")

class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query")

class CitationModel(BaseModel):
    document_id: str = Field(..., description="Document ID")
    filing_type: str = Field(..., description="Filing type")
    company: str = Field(..., description="Company ticker or name")
    year: int = Field(..., description="Filing year")
    quarter: Optional[int] = Field(None, description="Filing quarter (for 10-Q)")
    location: str = Field(..., description="Location in the document")
    content: str = Field(..., description="Cited content")

class QueryResponse(BaseModel):
    response: str = Field(..., description="Response to the query")
    citations: List[CitationModel] = Field(..., description="Citations for the response")

# Dependency for getting components
def get_components(db: Session = Depends(get_db_session)):
    # Initialize components
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not found")
    
    # Create repositories
    document_repo = DocumentRepository(db)
    
    # Create components
    edgar_client = EdgarClient()
    document_processor = DocumentProcessor()
    embedder = Embedder(api_key=api_key)
    vector_store = VectorStore()
    query_analyzer = QueryAnalyzer(api_key=api_key)
    document_selector = DocumentSelector(document_repo.get_document_registry())
    content_retriever = ContentRetriever(vector_store, embedder, api_key=api_key)
    response_generator = ResponseGenerator(document_repo.get_document_metadata_store(), api_key=api_key)
    
    return {
        "edgar_client": edgar_client,
        "document_processor": document_processor,
        "embedder": embedder,
        "vector_store": vector_store,
        "query_analyzer": query_analyzer,
        "document_selector": document_selector,
        "content_retriever": content_retriever,
        "response_generator": response_generator,
        "document_repo": document_repo
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the Farsight2 API"}

@app.post("/process", response_model=ProcessDocumentResponse)
async def process_document(request: ProcessDocumentRequest, components=Depends(get_components), db: Session = Depends(get_db_session)):
    """Process a 10-K/10-Q document."""
    try:
        # Get components
        edgar_client: EdgarClient = components["edgar_client"]
        document_processor: DocumentProcessor = components["document_processor"]
        embedder: Embedder = components["embedder"]
        vector_store: VectorStore = components["vector_store"]
        document_repo: DocumentRepository = components["document_repo"]
        
        # Validate filing type
        if request.filing_type not in ["10-K", "10-Q"]:
            raise HTTPException(status_code=400, detail="Invalid filing type. Must be 10-K or 10-Q")
        
        # Validate quarter
        if request.filing_type == "10-Q" and (request.quarter is None or request.quarter not in [1, 2, 3]):
            raise HTTPException(status_code=400, detail="For 10-Q filings, quarter must be 1, 2, or 3")
        
        # Get company filings
        try:
            filings = edgar_client.get_company_filings(request.ticker)
        except Exception as e:
            logger.error(f"Error getting company filings: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting company filings: {str(e)}")
        
        # Find the requested filing
        # This is a simplified implementation
        # In a real implementation, you would parse the filings to find the right one
        # accession_number = f"{request.ticker}_{request.filing_type}_{request.year}"
        # if request.quarter:
        #     accession_number += f"_Q{request.quarter}"
        
        # Download the filing
        try:
            filing_result = edgar_client.download_filing(
                ticker=request.ticker,
                filing_type=request.filing_type,
                year=request.year,
                quarter=request.quarter
            )
        except Exception as e:
            logger.error(f"Error downloading filing: {e}")
            raise HTTPException(status_code=500, detail=f"Error downloading filing: {str(e)}")
        
        # Process the filing
        try:
            parsed_document = document_processor.process_filing(
                file_path=filing_result["file_path"],
                metadata=filing_result["metadata"]
            )
        except Exception as e:
            logger.error(f"Error processing filing: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing filing: {str(e)}")
        
        # Save document to database
        try:
            document_repo.create_document(parsed_document.metadata)
        except Exception as e:
            logger.error(f"Error saving document to database: {e}")
            raise HTTPException(status_code=500, detail=f"Error saving document to database: {str(e)}")
        
        # Generate embeddings
        try:
            embedded_chunks = embedder.embed_document(parsed_document)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise HTTPException(status_code=500, detail=f"Error generating embeddings: {str(e)}")
        
        # Add to vector store
        try:
            vector_store.add_embedded_chunks(embedded_chunks)
        except Exception as e:
            logger.error(f"Error adding to vector store: {e}")
            raise HTTPException(status_code=500, detail=f"Error adding to vector store: {str(e)}")
        
        # Return response
        return {
            "document_id": parsed_document.document_id,
            "ticker": request.ticker,
            "year": request.year,
            "quarter": request.quarter,
            "filing_type": request.filing_type,
            "filing_date": parsed_document.metadata.filing_date.isoformat() if parsed_document.metadata.filing_date else None,
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, components=Depends(get_components), db: Session = Depends(get_db_session)):
    """Query the system with a natural language question."""
    try:
        # Get components
        query_analyzer = components["query_analyzer"]
        document_selector = components["document_selector"]
        content_retriever = components["content_retriever"]
        response_generator = components["response_generator"]
        
        # Analyze the query
        try:
            query_analysis = query_analyzer.analyze_query(request.query)
        except Exception as e:
            logger.error(f"Error analyzing query: {e}")
            raise HTTPException(status_code=500, detail=f"Error analyzing query: {str(e)}")
        
        # Select documents
        try:
            document_references = document_selector.select_documents(query_analysis)
        except Exception as e:
            logger.error(f"Error selecting documents: {e}")
            raise HTTPException(status_code=500, detail=f"Error selecting documents: {str(e)}")
        
        # If no documents found, return error
        if not document_references:
            raise HTTPException(status_code=404, detail="No relevant documents found for the query")
        
        # Retrieve relevant content
        try:
            relevant_chunks = content_retriever.retrieve_content(
                query=request.query,
                query_analysis=query_analysis,
                document_references=document_references
            )
        except Exception as e:
            logger.error(f"Error retrieving content: {e}")
            raise HTTPException(status_code=500, detail=f"Error retrieving content: {str(e)}")
        
        # If no relevant chunks found, return error
        if not relevant_chunks:
            raise HTTPException(status_code=404, detail="No relevant content found for the query")
        
        # Generate response
        try:
            formatted_response = response_generator.generate_response(
                query=request.query,
                relevant_chunks=relevant_chunks
            )
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")
        
        # Convert citations to the response model format
        citations = [
            CitationModel(
                document_id=citation.document_id,
                filing_type=citation.filing_type,
                company=citation.company,
                year=citation.year,
                quarter=citation.quarter,
                location=citation.location,
                content=citation.content
            )
            for citation in formatted_response.citations
        ]
        
        # Return response
        return {
            "response": formatted_response.response,
            "citations": citations
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 