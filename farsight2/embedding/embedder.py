"""Embedder for generating embeddings from document chunks."""

import logging
import os
from typing import List, Optional
import json

from openai import OpenAI

from farsight2.models.models import (
    DocumentChunk,
    EmbeddedChunk,
    ParsedDocument
)

logger = logging.getLogger(__name__)

class Embedder:
    """Embedder for generating embeddings from document chunks."""
    
    def __init__(self, api_key: Optional[str] = None, output_dir: Optional[str] = None):
        """Initialize the embedder.
        
        Args:
            api_key: OpenAI API key
            output_dir: Directory to save embeddings
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "../../data/embeddings")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Default embedding model
        self.embedding_model = "text-embedding-3-small"
    
    def embed_document(self, parsed_document: ParsedDocument) -> List[EmbeddedChunk]:
        """Generate embeddings for all chunks in a document.
        
        Args:
            parsed_document: Parsed document to embed
            
        Returns:
            List of embedded chunks
        """
        logger.info(f"Embedding document: {parsed_document.document_id}")
        
        # Convert document chunks to a format suitable for embedding
        document_chunks = self._convert_to_document_chunks(parsed_document)
        
        # Generate embeddings for all chunks
        embedded_chunks = []
        for chunk in document_chunks:
            embedding = self._generate_embedding(chunk.content)
            embedded_chunk = EmbeddedChunk(
                chunk=chunk,
                embedding=embedding
            )
            embedded_chunks.append(embedded_chunk)
        
        # Save the embeddings
        self._save_embeddings(embedded_chunks, parsed_document.document_id)
        
        return embedded_chunks
    
    def _convert_to_document_chunks(self, parsed_document: ParsedDocument) -> List[DocumentChunk]:
        """Convert parsed document components to document chunks for embedding."""
        document_chunks = []
        
        # Convert text chunks
        for text_chunk in parsed_document.text_chunks:
            chunk = DocumentChunk(
                chunk_id=text_chunk.chunk_id,
                document_id=text_chunk.document_id,
                content=text_chunk.text,
                content_type="text",
                location=f"Section: {text_chunk.section}"
            )
            document_chunks.append(chunk)
        
        # Convert tables
        for table in parsed_document.tables:
            # For tables, we'll use the HTML content as the content for embedding
            chunk = DocumentChunk(
                chunk_id=table.chunk_id,
                document_id=table.document_id,
                content=table.table_html,
                content_type="table",
                location=f"Section: {table.section}"
            )
            document_chunks.append(chunk)
        
        # Convert charts
        for chart in parsed_document.charts:
            # For charts, we'll use the caption as the content for embedding
            if chart.caption:
                chunk = DocumentChunk(
                    chunk_id=chart.chunk_id,
                    document_id=chart.document_id,
                    content=chart.caption,
                    content_type="chart",
                    location=f"Section: {chart.section}"
                )
                document_chunks.append(chunk)
        
        return document_chunks
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding for a text using OpenAI's API."""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return a zero vector as a fallback
            return [0.0] * 1536  # Default dimension for OpenAI embeddings
    
    def _save_embeddings(self, embedded_chunks: List[EmbeddedChunk], document_id: str) -> None:
        """Save embeddings to disk."""
        # Create a filename based on the document ID
        filename = f"{document_id}_embeddings.json"
        file_path = os.path.join(self.output_dir, filename)
        
        # Convert embedded chunks to a dictionary
        embeddings_dict = {
            "document_id": document_id,
            "chunks": [
                {
                    "chunk_id": chunk.chunk.chunk_id,
                    "document_id": chunk.chunk.document_id,
                    "content": chunk.chunk.content,
                    "content_type": chunk.chunk.content_type,
                    "location": chunk.chunk.location,
                    "embedding": chunk.embedding
                }
                for chunk in embedded_chunks
            ]
        }
        
        # Save the embeddings as JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(embeddings_dict, f) 