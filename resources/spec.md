Farsight2: 10-K/10-Q Digestion and Retrieval System Specification

1. Project Overview
   Farsight2 is a comprehensive system designed to process, analyze, and query SEC 10-K and 10-Q filings from public companies. The system allows users to ask natural language questions about company financial data and receive accurate, well-cited responses sourced directly from official filings.
   1.1 Core Objectives
   Fast and accurate retrieval of information from 10-K/10-Q documents
   Low latency for query responses
   High accuracy of information retrieval
   Proper source citation for all responses
   Ability to handle various data formats (text, tables, charts)
2. System Architecture
   The system is built with a modular architecture focusing on three primary workflows:
   2.1 Document Processing Flow
   Document acquisition from SEC EDGAR database
   Document parsing and content extraction (text, tables, charts)
   Content chunking and embedding generation
   Storage in document store and vector database
   2.2 Query Processing Flow
   Natural language query analysis
   Relevant document selection
   Content retrieval using vector similarity search
   Response generation with citations
   Response formatting and delivery
   2.3 Evaluation Flow
   Test suite generation for various companies
   Systematic query processing
   Response evaluation against expected answers
   Performance metrics calculation and reporting
3. Technical Components
   3.1 Database Structure
   PostgreSQL with pgvector extension for vector similarity search
   Core tables:
   companies: Company metadata (ticker, name)
   documents: Document metadata (ID, ticker, year, quarter, type)
   document_chunks: Extracted content chunks
   chunk_embeddings: Vector embeddings of document chunks
   text_chunks, tables, charts: Specific content type storage
   test_suites, test_questions, evaluation_results: Evaluation data
   3.2 Core Modules
   3.2.1 Document Processing
   edgar_client.py: Handles API interaction with SEC EDGAR
   document_processor.py: Extracts and processes content from documents
   3.2.2 Embedding
   embedder.py: Generates vector embeddings using OpenAI API
   3.2.3 Vector Storage
   vector_store.py: Manages vector storage and similarity search using pgvector
   3.2.4 Query Processing
   query_analyzer.py: Extracts key information from queries (companies, years, quarters)
   document_selector.py: Determines which documents are needed
   content_retriever.py: Retrieves relevant content using vector search
   response_generator.py: Generates responses with citations
   3.2.5 API
   app.py: FastAPI application providing endpoints for processing and querying
   3.2.6 Evaluation
   test_suite.py: Generates test suites and evaluates system performance
   3.3 Infrastructure
   Docker containerization for both application and database
   Docker Compose for orchestration
   Environment variable configuration for API keys and settings
4. API Endpoints
   4.1 Processing Endpoint
   Path: /process
   Method: POST
   Function: Processes a 10-K or 10-Q filing and stores it in the system
   Parameters:
   ticker: Company ticker symbol
   year: Filing year
   quarter: Filing quarter (null for 10-K)
   filing_type: Type of filing (10-K or 10-Q)
   4.2 Query Endpoint
   Path: /query
   Method: POST
   Function: Processes natural language queries about companies
   Parameters:
   query: Natural language query text
   Response: Answer with citations to source documents
5. Development and Deployment
   5.1 Development Environment
   Poetry for dependency management
   Docker and Docker Compose for local development
   Environment variables for configuration
   5.2 Deployment Scripts
   run_dev.sh: Starts the application in development mode
   run_prod.sh: Starts the application in production mode
   reset_db.sh: Resets the database
   stop.sh: Stops all containers
   5.3 Testing Framework
   Unit tests for core components
   Test suites for evaluation
   Test database connection script
6. Data Flow
   User submits a document processing request via API
   System downloads document from SEC EDGAR
   Document is processed, chunked, and embedded
   Embeddings and document chunks are stored in the database
   User submits a query via API
   Query is analyzed to extract key information
   Relevant documents are selected based on query analysis
   Relevant content is retrieved using vector similarity search
   Response is generated with citations
   Response is returned to the user
7. Technology Stack
   Backend: Python with FastAPI
   Database: PostgreSQL with pgvector extension
   Containerization: Docker and Docker Compose
   AI/ML: OpenAI API for embeddings and language models
   Testing: Python unittest framework
   Dependency Management: Poetry
8. Design Considerations and Tradeoffs
   8.1 Accuracy vs. Latency
   Preprocessing documents for faster query responses
   Using vector search for efficient content retrieval
   Implementing reranking for improved accuracy
   8.2 Storage vs. Processing
   Storing processed documents and embeddings for faster retrieval
   Processing documents on-demand when necessary
   8.3 Modularity vs. Integration
   Designing with distinct modules for flexibility
   Ensuring smooth integration between components
9. Future Enhancements
   Improved document parsing for complex tables and charts
   Support for additional filing types
   Cross-company comparison capabilities
   Web UI for easier interaction
   Horizontal scaling support
   Database migrations with Alembic
   This specification provides a comprehensive overview of the Farsight2 system architecture, components, and workflows that would enable an LLM to
