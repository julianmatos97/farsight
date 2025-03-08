## Main Application Flow

1. **Document Processing Flow**:

   - User requests processing of a specific 10-K/10-Q document
   - System downloads the document from EDGAR
   - Document is processed to extract text, tables, charts, and metadata
   - Processed document is stored in the document store
   - Document chunks are embedded and stored in the vector store
   - Company and document are registered in the company registry

2. **Query Processing Flow**:

   - User submits a natural language query
   - Query analyzer extracts key information from the query
   - Document selector determines which documents are needed
   - Relevant content retriever finds the most relevant chunks
   - Response generator creates a response based on the relevant content
   - Citations are generated for the sources used
   - Response is formatted with citations and returned to the user

3. **Evaluation Flow**:
   - Test suite is generated with questions and expected answers
   - System processes each question in the test suite
   - Responses are compared to expected answers
   - Metrics are calculated to evaluate system performance

This architecture is designed to be modular, maintainable, and focused on the key requirements of accuracy, latency, and source tracking. Each component has a clear responsibility, making the system easier to develop, test, and extend.
