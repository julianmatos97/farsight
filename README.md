# Farsight2: 10-K/10-Q Digestion and Retrieval System

Farsight2 is a system for processing, analyzing, and querying 10-K and 10-Q filings from public companies. It allows users to ask natural language questions about company financial data and receive accurate responses with citations to the source documents.

## Project Overview

This project addresses the need for financial professionals to quickly extract specific information from lengthy 10-K and 10-Q filings. Instead of manually searching through documents that can be tens or hundreds of pages long, Farsight2 provides a natural language interface to retrieve precise answers with proper source citations.

### Core Value Proposition

The system is designed around three key performance values as specified in the project requirements:

1. **Low Latency**: By preprocessing documents and using efficient vector retrieval, the system minimizes query-to-response time
2. **High Accuracy**: Using a combination of semantic search and LLM-based analysis to ensure correct answers
3. **Source Tracking**: All responses include citations to the original documents for verification and audit

## Features

- Download 10-K and 10-Q filings from the SEC EDGAR database
- Process and extract text, tables, and charts from filings
- Generate embeddings for document chunks for efficient retrieval
- Analyze natural language queries to understand intent
- Retrieve relevant content from processed documents
- Generate accurate responses with citations to source documents
- Evaluate system performance using test suites
- Containerized deployment with Docker and Docker Compose
- PostgreSQL database with pgvector for vector storage and similarity search

## Architecture

The system is designed with a modular architecture focused on three main flows:

1. **Document Processing Flow**:

   - Download documents from EDGAR
   - Process documents to extract content (including text, tables, and charts)
   - Generate embeddings for document chunks
   - Store processed documents and embeddings in PostgreSQL

2. **Query Processing Flow**:

   - Analyze queries to extract key information
   - Select relevant documents based on company and timeframe
   - Retrieve relevant content using vector similarity search
   - Generate accurate responses with proper citations

3. **Evaluation Flow**:
   - Generate test suites with questions
   - Process questions through the system
   - Evaluate system performance against ground truth

## Technical Implementation

The system implements the three core technical processes specified in the project requirements:

1. **Preprocessing**: Documents are processed to extract text, tables, and charts, which are then chunked and embedded for efficient retrieval
2. **Document Selection**: The system analyzes queries to determine which 10-K/10-Q documents are relevant
3. **Relevance Determination**: Vector similarity and reranking are used to identify the most relevant document sections for answering queries

## Installation

### Prerequisites

- Docker and Docker Compose
- OpenAI API key

### Setup

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/farsight2.git
   cd farsight2
   ```

2. Create a `.env` file with your OpenAI API key:

   ```
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. Build and start the containers:
   ```
   docker-compose up -d
   ```

## Usage

### API Endpoints

The system provides the two required API endpoints as specified in the project requirements:

1. **Processing Endpoint**: To ingest and process 10-K/10-Q filings
2. **Inference Endpoint**: To answer natural language queries with cited sources

### Processing a Document

Use the `/process` endpoint to process a 10-K or 10-Q filing:

```
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "year": 2023,
    "quarter": null,
    "filing_type": "10-K"
  }'
```

### Querying the System

Use the `/query` endpoint to ask questions about processed documents:

```
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What was Apple's revenue in 2023?"
  }'
```

### Test Suite and Evaluation

As required by the project specifications, the system includes a comprehensive test suite covering at least 5 different companies over 3 years of filings, with questions targeting various information types (text, tables, charts).

#### Generating a Test Suite

```
docker-compose exec app python -m farsight2.main test-suite --company AAPL --years 2021 2022 2023 --name apple_test
```

#### Running an Evaluation

```
docker-compose exec app python -m farsight2.main evaluate --test-suite apple_test --name apple_evaluation
```

### Initializing the Database

```
docker-compose exec app python -m farsight2.main init-db
```

## API Documentation

Once the API is running, you can access the Swagger documentation at http://localhost:8000/docs.

## Project Structure

```
farsight2/
├── data/                      # Data storage (mounted as volume)
│   ├── downloads/             # Downloaded filings
│   ├── processed/             # Processed documents
│   ├── embeddings/            # Document embeddings (legacy)
│   ├── test_suites/           # Test suites
│   └── evaluation_results/    # Evaluation results
├── docker/                    # Docker configuration
│   └── postgres/              # PostgreSQL configuration
│       └── init-pgvector.sql  # SQL script to initialize pgvector
├── farsight2/                 # Main package
│   ├── api/                   # API module
│   │   ├── __init__.py
│   │   └── app.py             # FastAPI application
│   ├── database/              # Database module
│   │   ├── __init__.py
│   │   ├── db.py              # Database connection
│   │   ├── init_db.py              # Database connection
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── repository_factory.py      # Repository pattern for database operations
│   │   ├── repository.py      # Repository pattern for database operations
|   |   └── unified_repository.py
│   ├── document_processing/   # Document processing module
│   │   ├── __init__.py
│   │   ├── edgar_client.py    # EDGAR API client
│   │   └── document_processor.py # Document processor
│   ├── embedding/             # Embedding module
│   │   ├── __init__.py
│   │   └── unified_embedding_service.py        # Embedder
│   ├── models/                # Data models
│   │   ├── __init__.py
│   │   └── models.py          # Pydantic models
│   ├── query_processing/      # Query processing module
│   │   ├── __init__.py
│   │   ├── query_analyzer.py  # Query analyzer
│   │   ├── document_selector.py # Document selector
│   │   ├── content_retriever.py # Content retriever
│   │   └── response_generator.py # Response generator
│   ├── __init__.py
│   ├── main.py                # Main script
│   └── utils.py               # Utility functions
├── tests/                     # Tests
├── Dockerfile                 # Dockerfile for the application
├── docker-compose.yml         # Docker Compose configuration
└── README.md                  # This file
```

## Design Decisions and Tradeoffs

The system is designed with the following considerations:

1. **Latency vs. Accuracy**: We've optimized for low query-response latency by preprocessing documents and using vector embeddings, while maintaining high accuracy through contextual retrieval and LLM-based analysis.

2. **Source Tracking**: All responses include citations to the original documents, allowing users to verify information and understand its context.

3. **Modularity**: The system uses a modular architecture to facilitate easy updates and component replacement.

4. **Storage Efficiency**: By using PostgreSQL with pgvector, we maintain efficient storage and retrieval without requiring specialized vector database services.

5. **Document Processing**: Special attention is given to properly extracting and representing tables and charts, which are critical in financial documents.

## Supported Companies

The system currently has comprehensive test coverage for the following companies' filings over the past three years:

- Apple (AAPL)
- Microsoft (MSFT)
- Google/Alphabet (GOOGL)
- Amazon (AMZN)
- Tesla (TSLA)

## Installation Instructions

1. Clone the repository
2. Create a `.env` file with your OpenAI API key
3. Run `docker-compose up -d`
4. Access the API at http://localhost:8000

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- OpenAI for providing the API used for embeddings and language models
- SEC for providing access to EDGAR filings
- pgvector for providing vector similarity search in PostgreSQL
