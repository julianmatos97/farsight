"""FastAPI application for the Farsight2 API."""

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from farsight2.document_processing.edgar_client import EdgarClient
from farsight2.document_processing.document_processor import DocumentProcessor
from farsight2.embedding.unified_embedding_service import UnifiedEmbeddingService
from farsight2.models.models import (
    DocumentMetadata,
    FactValue,
    ParsedDocument,
    RelevantChunk,
)
from farsight2.query_processing.query_analyzer import QueryAnalyzer
from farsight2.query_processing.document_selector import DocumentSelector
from farsight2.query_processing.content_retriever import ContentRetriever
from farsight2.query_processing.response_generator import ResponseGenerator
from farsight2.database.db import get_db_session, init_db
from farsight2.database.repository import (
    DocumentRepository,
    FactRepository,
)
from dotenv import load_dotenv
import traceback

load_dotenv()
from farsight2.database.unified_repository import UnifiedRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Farsight2 API",
    description="API for processing and querying 10-K/10-Q filings",
    version="0.1.0",
)


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize the database when the application starts."""
    init_db()
    logger.info("Database initialized")


# Request and response models
class ProcessDocumentRequest(BaseModel):
    """Request model for processing SEC documents."""

    ticker: str = Field(..., description="Company ticker symbol")
    year: int = Field(..., description="Filing year")
    quarter: Optional[int] = Field(None, description="Filing quarter (for 10-Q)")
    filing_type: str = Field(..., description="Filing type (10-K or 10-Q)")


class ProcessDocumentResponse(BaseModel):
    """Response model for document processing results."""

    document_id: str = Field(..., description="Document ID")
    ticker: str = Field(..., description="Company ticker symbol")
    year: int = Field(..., description="Filing year")
    quarter: Optional[int] = Field(None, description="Filing quarter (for 10-Q)")
    filing_type: str = Field(..., description="Filing type (10-K or 10-Q)")
    filing_date: str = Field(..., description="Filing date")
    status: str = Field(..., description="Processing status")


class QueryRequest(BaseModel):
    """Request model for natural language queries."""

    query: str = Field(..., description="Natural language query")


class CitationModel(BaseModel):
    """Model for citation information in query responses."""

    document_id: str = Field(..., description="Document ID")
    filing_type: str = Field(..., description="Filing type")
    company: str = Field(..., description="Company ticker or name")
    year: int = Field(..., description="Filing year")
    quarter: Optional[int] = Field(None, description="Filing quarter (for 10-Q)")
    location: str = Field(..., description="Location in the document")
    content: str = Field(..., description="Cited content")
    content_type: str = Field(..., description="Content type")
    fact_id: Optional[str] = Field(None, description="Fact ID")


class QueryResponse(BaseModel):
    """Response model for query results with citations."""

    response: str = Field(..., description="Response to the query")
    citations: List[CitationModel] = Field(
        ..., description="Citations for the response"
    )
    documents_used: List[str] = Field(..., description="Documents used for the query")
    facts_used: List[FactValue] = Field(..., description="Facts used for the query")


# Dependency for getting components
def get_components(db: Session = Depends(get_db_session)):
    """
    Dependency injection for application components.
    Initializes and provides access to all major system components.
    """
    # Initialize components
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not found")

    # Create repositories
    document_repo = DocumentRepository(db)
    fact_repo = FactRepository(db)

    unified_repository = UnifiedRepository()
    # Create components
    edgar_client = EdgarClient()
    document_processor = DocumentProcessor()
    embedding_service = UnifiedEmbeddingService(
        api_key=api_key, repository=unified_repository
    )
    query_analyzer = QueryAnalyzer(api_key=api_key)
    document_selector = DocumentSelector()
    content_retriever = ContentRetriever(embedding_service, unified_repository)
    response_generator = ResponseGenerator(
        document_repo.get_document_metadata_store(), api_key=api_key
    )

    return {
        "edgar_client": edgar_client,
        "document_processor": document_processor,
        "embedding_service": embedding_service,
        "query_analyzer": query_analyzer,
        "document_selector": document_selector,
        "content_retriever": content_retriever,
        "response_generator": response_generator,
        "document_repo": document_repo,
        "unified_repository": unified_repository,
        "fact_repo": fact_repo,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the Farsight2 API"}


@app.post("/process", response_model=ProcessDocumentResponse)
async def process_document(
    request: ProcessDocumentRequest,
    components=Depends(get_components),
):
    """
    Process a 10-K/10-Q document.

    This endpoint handles the entire document processing pipeline:
    1. Validates the request
    2. Downloads XBRL facts for new companies
    3. Downloads the SEC filing
    4. Processes and parses the document
    5. Generates embeddings for document chunks
    6. Stores everything in the database
    """
    try:
        # Get components
        edgar_client: EdgarClient = components["edgar_client"]
        document_processor: DocumentProcessor = components["document_processor"]
        embedding_service: UnifiedEmbeddingService = components["embedding_service"]
        document_repo: DocumentRepository = components["document_repo"]
        unified_repository: UnifiedRepository = components["unified_repository"]

        # Validate filing type
        if request.filing_type not in ["10-K", "10-Q"]:
            raise HTTPException(
                status_code=400, detail="Invalid filing type. Must be 10-K or 10-Q"
            )

        # Validate quarter
        if  request.quarter not in [1, 2, 3, 4]:
            raise HTTPException(
                status_code=400, detail="Quarter must be 1, 2, 3, or 4"
            )

        # Get company filings
        try:
            filings = edgar_client.get_company_filings(request.ticker)
        except Exception as e:
            logger.error(f"Error getting company filings: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error getting company filings: {str(e)}"
            )

        # Check if document already exists - return early if it does
        if document := unified_repository.get_document(
            request.ticker, request.year, request.quarter, request.filing_type
        ):
            return {
                "document_id": document.document_id,
                "ticker": request.ticker,
                "year": request.year,
                "quarter": request.quarter,
                "filing_type": request.filing_type,
                "filing_date": document.filing_date.isoformat()
                if document.filing_date
                else None,
                "status": "success",
            }

        try:
            # First time you see the company, download the XBRL facts
            if unified_repository.get_company(request.ticker) is None:
                facts, _ = edgar_client.download_xbrl_facts(request.ticker)
            else:
                facts = []
                fact_values = []
        except Exception as e:
            logger.error(f"Error downloading XBRL facts: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error downloading XBRL facts: {str(e)}"
            )

        try:
            # Download the actual filing document from SEC EDGAR
            filing_result: Dict[str, str | DocumentMetadata] = (
                edgar_client.download_filing(
                    ticker=request.ticker,
                    filing_type=request.filing_type,
                    year=request.year,
                    quarter=request.quarter,
                )
            )

        except Exception as e:
            logger.error(f"Error downloading filing: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error downloading filing: {str(e)}"
            )

        # Process the filing - extract sections, tables, etc.
        try:
            parsed_document: ParsedDocument = document_processor.process_filing(
                content=filing_result["content"], metadata=filing_result["metadata"]
            )

        except Exception as e:
            logger.error(f"Error processing filing: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500, detail=f"Error processing filing: {str(e)}"
            )

        # Save document metadata to database
        try:
            document_repo.create_document(parsed_document.metadata)
        except Exception as e:
            logger.error(f"Error saving document to database: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500, detail=f"Error saving document to database: {str(e)}"
            )

        # Generate embeddings for document chunks
        try:
            embedding_service.embed_document(parsed_document)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500, detail=f"Error generating embeddings: {str(e)}"
            )

        # Generate embeddings for XBRL facts if available
        try:
            if len(facts) > 0:
                embedding_service.embed_facts(facts)
        except Exception as e:
            logger.error(f"Error saving document to unified repository: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Error saving document to unified repository: {str(e)}",
            )

        # Return response with document details
        return {
            "document_id": parsed_document.document_id,
            "ticker": request.ticker,
            "year": request.year,
            "quarter": request.quarter,
            "filing_type": request.filing_type,
            "filing_date": parsed_document.metadata.filing_date.isoformat()
            if parsed_document.metadata.filing_date
            else None,
            "status": "success",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error processing document: {str(e)}"
        )


@app.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    components=Depends(get_components),
):
    """
    Query the system with a natural language question.

    This endpoint handles the entire query processing pipeline:
    1. Analyzes the query to understand intent and entities
    2. Selects relevant documents based on the query
    3. Retrieves relevant content chunks and XBRL facts
    4. Generates a comprehensive response with citations
    """
    try:
        # Get components
        query_analyzer: QueryAnalyzer = components["query_analyzer"]
        document_selector: DocumentSelector = components["document_selector"]
        content_retriever: ContentRetriever = components["content_retriever"]
        response_generator: ResponseGenerator = components["response_generator"]
        fact_repo: FactRepository = components["fact_repo"]
        unified_repository: UnifiedRepository = components["unified_repository"]

        # Analyze the query - extract entities, intent, and generate embedding
        try:
            query_analysis = query_analyzer.analyze_query(request.query)
        except Exception as e:
            logger.error(f"Error analyzing query: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error analyzing query: {str(e)}"
            )

        # Select relevant documents based on query analysis
        try:
            document_references = document_selector.select_documents(query_analysis)
        except Exception as e:
            logger.error(f"Error selecting documents: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error selecting documents: {str(e)}"
            )

        # If no documents found, return error
        if not document_references:
            pass
            # raise HTTPException(status_code=404, detail="No relevant documents found for the query")

        # Retrieve relevant content from documents and XBRL facts
        try:
            # Get relevant document chunks using semantic search
            relevant_chunks: List[RelevantChunk] = content_retriever.retrieve_content(
                query=request.query,
                query_analysis=query_analysis,
                document_references=document_references,
            )

            relevant_doc_ids = set(
                [chunk.chunk.document_id for chunk in relevant_chunks]
            )
            print(f"Relevant doc ids: {relevant_doc_ids}")
            # Search for facts using the query embedding
            relevant_facts = fact_repo.search_facts_by_embedding(
                query_analysis.embedding
            )
            logger.info(f"Relevant facts: {relevant_facts}")

            # Get fact values for specific companies and years if provided in the query
            fact_values = []

            for company in query_analysis.companies:
                for year in query_analysis.years:
                    for quarter in [1, 2, 3, 4]:
                        for filing_type in ["10K", "10Q"]:
                            for i, fact in enumerate(relevant_facts):
                                # Get fact values for this company and year
                                values_for_fact = unified_repository.get_fact_values_by_details(
                                    fact.fact_id, company, year, quarter, filing_type
                                )
                                if values_for_fact:
                                    fact_values.extend([(fact_value, relevant_facts[i].description) for fact_value in values_for_fact])
            logger.info(f"Fact values: {fact_values}")

        except Exception as e:
            logger.error(f"Error retrieving content: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500, detail=f"Error retrieving content: {str(e)}"
            )

        # If no relevant content found, return error
        if not relevant_chunks and not relevant_facts and not fact_values:
            raise HTTPException(
                status_code=404, detail="No relevant content found for the query"
            )

        # Generate comprehensive response with citations
        try:
            formatted_response = response_generator.generate_response(
                query=request.query,
                relevant_chunks=relevant_chunks,
                relevant_fact_values=fact_values,
            )
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500, detail=f"Error generating response: {str(e)}"
            )

        # Convert citations to the response model format
        citations = [
            CitationModel(
                document_id=citation.document_id,
                filing_type=citation.filing_type,
                company=citation.company,
                year=citation.year,
                quarter=citation.quarter,
                location=citation.location,
                content=citation.content,
                content_type=citation.content_type,  # Added content type for better source tracking
                fact_id=citation.fact_id
                if hasattr(citation, "fact_id")
                else None,  # Added fact ID for XBRL citations
            )
            for citation in formatted_response.citations
        ]

        # Return response with enhanced metadata
        return {
            "response": formatted_response.response,
            "citations": citations,
            "documents_used": [doc.document_id for doc in document_references],
            "facts_used": [fact_value[0] for fact_value in fact_values] if fact_values else [],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
