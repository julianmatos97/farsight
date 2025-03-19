"""
Unified embedding service that handles both embedding generation and vector search.

This module combines functionality from the Embedder and VectorStore classes
to provide a streamlined API for working with embeddings.
"""

from concurrent.futures import ThreadPoolExecutor
import logging
import os
from typing import List, Dict, Any, Optional, Tuple

from openai import OpenAI
import numpy as np

from farsight2.models.models import (
    DocumentChunk,
    EmbeddedChunk,
    QueryAnalysis,
    RelevantChunk,
    ParsedDocument,
    DocumentMetadata,
    Fact,
)
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class UnifiedEmbeddingService:
    """
    Unified service for generating, storing, and retrieving embeddings.

    This class combines functionality from the Embedder and VectorStore classes
    to provide a streamlined API for working with embeddings.
    """

    def __init__(self, api_key: Optional[str] = None, repository=None):
        """
        Initialize the unified embedding service.

        Args:
            api_key: OpenAI API key (defaults to environment variable)
            repository: Repository for database access (defaults to a new instance)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.api_key = "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"
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)
        self.repository = repository
        self.response_model = "gpt-4o"

        # Default embedding model
        self.embedding_model = os.environ.get(
            "EMBEDDING_MODEL", "text-embedding-3-large"
        )

    def embed_fact(self, fact: Fact) -> List[float]:
        """
        Generate an embedding for a fact based on its label and description.

        Args:
            fact: Fact model containing label and description

        Returns:
            Vector embedding as a list of floats
        """
        # Combine label and description into a single text
        text = f"{fact.label} {fact.description}"
        return self.generate_embedding(text)

    def embed_facts(self, facts: List[Fact]) -> List[Fact]:
        """
        Generate embeddings for a list of facts.

        Args:
            facts: List of facts to embed

        Returns:
            List of facts with embeddings added
        """
        logger.info(f"Generating embeddings for {len(facts)} facts")

        embedded_facts = []

        def embed_single_fact(fact):
            try:
                _fact = self.repository.get_fact(fact.fact_id)
                if _fact is not None and _fact.embedding is not None:
                    logger.info(f"Fact already exists: {fact.fact_id}")
                    return fact
                fact.embedding = self.embed_fact(fact)
                self.repository.create_fact(fact)
                return fact
            except Exception as e:
                logger.error(f"Error embedding fact {fact.fact_id}: {e}")
                return None

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(embed_single_fact, facts))

        # Filter out None values (failed embeddings)
        embedded_facts = [fact for fact in results if fact is not None]

        return embedded_facts

    def search_facts(self, query: str, top_k: int = 5) -> List[Tuple[Fact, float]]:
        """
        Search for facts using semantic similarity to a query.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of tuples containing (fact, similarity_score)
        """
        try:
            # Use repository's vector search functionality
            return self.repository._repos["fact"].search_facts_by_text(
                query, self, top_k
            )
        except Exception as e:
            logger.error(f"Error searching facts: {e}")
            return []

    def embed_document(self, parsed_document: ParsedDocument) -> List[EmbeddedChunk]:
        """
        Generate and store embeddings for all chunks in a document.

        This method:
        1. Converts document components to document chunks
        2. Generates embeddings for each chunk
        3. Stores the chunks and embeddings in the database

        Args:
            parsed_document: Parsed document to embed

        Returns:
            List of embedded chunks
        """
        logger.info(f"Embedding document: {parsed_document.document_id}")

        # Convert document chunks to a format suitable for embedding
        document_chunks = self._convert_to_document_chunks(parsed_document)

        # Generate embeddings and store in database
        embedded_chunks = []
        for chunk in document_chunks:
            embedding = self.generate_embedding(chunk.content)

            # Store the chunk and embedding in the database
            self.repository.create_content_chunk(chunk, embedding)

            # Create embedded chunk object for return value
            embedded_chunk = EmbeddedChunk(chunk=chunk, embedding=embedding)
            embedded_chunks.append(embedded_chunk)

        logger.info(
            f"Created {len(embedded_chunks)} embeddings for document {parsed_document.document_id}"
        )
        return embedded_chunks

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for text using OpenAI's API.

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing the embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        try:
            # Truncate text if it's too long (model dependent)
            max_tokens = 7000
            if len(text) > max_tokens * 4:  # Rough estimation of tokens
                logger.warning(
                    f"Text too long ({len(text)} chars), truncating to ~{max_tokens} tokens"
                )
                text = text[: max_tokens * 4]

            # Generate embedding via OpenAI API
            response = self.client.embeddings.create(
                model=self.embedding_model, input=text
            )
            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return a zero vector as a fallback
            return [0.0] * (3072 if "3-small" in self.embedding_model else 3072)

    def search(
        self, query: str, top_k: int = 5, filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[RelevantChunk]:
        """
        Search for chunks relevant to a query string.

        This high-level method:
        1. Generates an embedding for the query
        2. Searches for similar chunks in the database

        Args:
            query: Natural language query
            top_k: Number of results to return
            filter_dict: Dictionary of filters to apply (document_id, content_type, etc.)

        Returns:
            List of relevant chunks with their relevance scores
        """
        logger.info(f"Searching for chunks relevant to: {query}")

        # Generate embedding for the query
        query_embedding = self.generate_embedding(query)

        # Search for similar chunks
        return self.search_by_embedding(query_embedding, top_k, filter_dict)

    def search_by_embedding(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[RelevantChunk]:
        """
        Search for chunks similar to a query embedding.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_dict: Dictionary of filters to apply (document_id, content_type, etc.)

        Returns:
            List of relevant chunks with their relevance scores
        """
        logger.info(f"Searching for similar chunks (top_k={top_k})")

        # Use the repository to search for similar chunks
        return self.repository.search_embeddings(query_embedding, top_k, filter_dict)

    def search_documents(
        self, query: str, documents: List[DocumentMetadata], top_k: int = 5
    ) -> List[RelevantChunk]:
        """
        Search within specific documents for content relevant to a query.

        Args:
            query: Natural language query
            documents: List of documents to search within
            top_k: Number of results to return

        Returns:
            List of relevant chunks with their relevance scores
        """
        logger.info(f"Searching for '{query}' within {len(documents)} documents")

        # Extract document IDs
        document_ids = [doc.document_id for doc in documents]

        # Create filter
        filter_dict = {"document_id": document_ids[0]} if document_ids else None

        # Generate embedding and search
        query_embedding = self.generate_embedding(query)
        return self.search_by_embedding(query_embedding, top_k, filter_dict)

    def _convert_to_document_chunks(
        self, parsed_document: ParsedDocument
    ) -> List[DocumentChunk]:
        """
        Convert parsed document components to document chunks for embedding.

        Args:
            parsed_document: Parsed document with text chunks, tables, and charts

        Returns:
            List of document chunks ready for embedding
        """
        document_chunks = []

        # Convert text chunks
        for text_chunk in parsed_document.text_chunks:
            chunk = DocumentChunk(
                chunk_id=text_chunk.chunk_id,
                document_id=text_chunk.document_id,
                content=text_chunk.text,
                content_type="text",
                location=f"Section: {text_chunk.section}",
            )
            document_chunks.append(chunk)

        # Convert tables
        for table in parsed_document.tables:
            # For tables, we create a textual representation for embedding
            table_text = f"Table: {table.caption or 'Untitled'}\n"
            if table.table_data:
                # Convert structured data to text
                for row in table.table_data:
                    table_text += " | ".join(str(cell) for cell in row) + "\n"

            chunk = DocumentChunk(
                chunk_id=table.chunk_id,
                document_id=table.document_id,
                content=table_text,
                content_type="table",
                location=f"Section: {table.section}, Table: {table.caption or 'Untitled'}",
            )
            document_chunks.append(chunk)

        return document_chunks

    def embed_query_analysis(self, query_analysis: QueryAnalysis) -> List[float]:
        """
        Generate an embedding for a query analysis.

        This method enhances the original query with synonyms and related terms
        to improve semantic search for financial data queries.

        Args:
            query_analysis: The query analysis object containing the user's query

        Returns:
            Vector embedding as a list of floats
        """
        # Start with the original query
        original_query = query_analysis.query

        # Get enhanced query with synonyms from LLM
        response = self.client.chat.completions.create(
            model=self.response_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial data expert. Your task is to enhance the user's query by adding synonyms and related terms for financial concepts, metrics, time periods, and company names. Keep your response concise and focused on expanding the query with relevant financial terminology.",
                },
                {
                    "role": "user",
                    "content": f"Original query: {original_query}\n\nPlease enhance this query with relevant synonyms and related terms to improve semantic search.",
                },
            ],
            temperature=0.0,
        )

        enhanced_query = response.choices[0].message.content

        # Combine original and enhanced query for embedding
        text_to_embed = (
            f"Original Query: {original_query}\nEnhanced Query: {enhanced_query}"
        )

        return self.generate_embedding(text_to_embed)
