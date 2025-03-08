# Farsight2: 10-K/10-Q Digestion and Retrieval System

Farsight2 is a system for processing, analyzing, and querying 10-K and 10-Q filings from public companies. It allows users to ask natural language questions about company financial data and receive accurate responses with citations to the source documents.

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
   - Process documents to extract content
   - Generate embeddings for document chunks
   - Store processed documents and embeddings in PostgreSQL

2. **Query Processing Flow**:

   - Analyze queries to extract key information
   - Select relevant documents
   - Retrieve relevant content using vector similarity search
   - Generate responses with citations

3. **Evaluation Flow**:
   - Generate test suites with questions
   - Process questions through the system
   - Evaluate system performance

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

### Running the API

The API will be available at http://localhost:8000 after starting the containers.

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

### Generating a Test Suite

```
docker-compose exec app python -m farsight2.main test-suite --company AAPL --years 2021 2022 2023 --name apple_test
```

### Running an Evaluation

```
docker-compose exec app python -m farsight2.main evaluate --test-suite apple_test --name apple_evaluation
```

### Initializing the Database

The database is automatically initialized when the containers start, but you can also initialize it manually:

```
docker-compose exec app python -m farsight2.main init-db
```

## API Documentation

Once the API is running, you can access the Swagger documentation at http://localhost:8000/docs.

## Docker Containers

The system consists of two Docker containers:

1. **app**: The main application container running the FastAPI application
2. **postgres**: PostgreSQL database with pgvector extension for vector storage and similarity search

## Database Schema

The system uses PostgreSQL with the following tables:

- **companies**: Stores company information
- **documents**: Stores document metadata
- **document_chunks**: Stores document chunks
- **chunk_embeddings**: Stores embeddings for document chunks with pgvector
- **test_suites**: Stores test suites
- **test_questions**: Stores test questions
- **evaluation_results**: Stores evaluation results
- **evaluation_answers**: Stores evaluation answers

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
│   │   ├── models.py          # SQLAlchemy models
│   │   └── repository.py      # Repository pattern for database operations
│   ├── document_processing/   # Document processing module
│   │   ├── __init__.py
│   │   ├── edgar_client.py    # EDGAR API client
│   │   └── document_processor.py # Document processor
│   ├── embedding/             # Embedding module
│   │   ├── __init__.py
│   │   └── embedder.py        # Embedder
│   ├── evaluation/            # Evaluation module
│   │   ├── __init__.py
│   │   └── test_suite.py      # Test suite generator and evaluator
│   ├── models/                # Data models
│   │   ├── __init__.py
│   │   └── models.py          # Pydantic models
│   ├── query_processing/      # Query processing module
│   │   ├── __init__.py
│   │   ├── query_analyzer.py  # Query analyzer
│   │   ├── document_selector.py # Document selector
│   │   ├── content_retriever.py # Content retriever
│   │   └── response_generator.py # Response generator
│   ├── vector_store/          # Vector store module
│   │   ├── __init__.py
│   │   └── vector_store.py    # Vector store using pgvector
│   ├── __init__.py
│   └── main.py                # Main script
├── tests/                     # Tests
├── Dockerfile                 # Dockerfile for the application
├── Dockerfile.postgres        # Dockerfile for PostgreSQL with pgvector
├── docker-compose.yml         # Docker Compose configuration
├── pyproject.toml             # Poetry configuration
├── poetry.lock                # Poetry lock file
└── README.md                  # This file
```

## Design Decisions and Tradeoffs

The system is designed with the following considerations:

1. **Accuracy**: The system uses a combination of vector search and LLM-based reranking to ensure accurate retrieval of relevant content. Responses are generated with citations to source documents for transparency and verification.

2. **Latency**: The system uses a preprocessing step to extract and embed document content, allowing for fast retrieval at query time. The vector store is optimized for efficient similarity search using pgvector.

3. **Modularity**: The system is designed with a modular architecture, making it easy to replace or upgrade individual components. For example, the vector store could be replaced with a different solution if needed.

4. **Scalability**: The system is containerized using Docker and Docker Compose, making it easy to deploy and scale. The PostgreSQL database with pgvector provides efficient vector storage and similarity search.

5. **Persistence**: The system uses PostgreSQL for persistent storage of documents, embeddings, and evaluation results, ensuring that data is not lost when the containers are restarted.

## Future Improvements

- Implement more robust document parsing, especially for tables and charts
- Add support for more filing types beyond 10-K and 10-Q
- Improve query analysis for more complex queries
- Add support for cross-company comparisons
- Implement a more sophisticated evaluation framework
- Add a web UI for easier interaction with the system
- Implement database migrations using Alembic
- Add support for horizontal scaling with multiple application instances

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- OpenAI for providing the API used for embeddings and language models
- SEC for providing access to EDGAR filings
- pgvector for providing vector similarity search in PostgreSQL
