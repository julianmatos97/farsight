"""Vector store for storing and retrieving document chunk embeddings using PostgreSQL with pgvector."""

import logging
from typing import List, Dict, Any, Optional
import numpy as np


from farsight2.models.models import (
    EmbeddedChunk,
    RelevantChunk
)
from farsight2.database.db import SessionLocal
from farsight2.database.repository import EmbeddingRepository, ChunkRepository

logger = logging.getLogger(__name__)

class VectorStore:
    """Vector store for storing and retrieving document chunk embeddings using PostgreSQL with pgvector."""
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize the vector store.
        
        Args:
            data_dir: Directory containing embeddings (not used with PostgreSQL)
        """
        self.data_dir = data_dir  # Kept for backward compatibility
        self.db = SessionLocal()
        self.embedding_repo = EmbeddingRepository(self.db)
        self.chunk_repo = ChunkRepository(self.db)
        self.loaded = True  # Always loaded with PostgreSQL
    
    def load(self) -> None:
        """Load all embeddings from the database.
        
        This is a no-op with PostgreSQL as data is loaded on demand.
        """
        # No need to load anything, as we're using PostgreSQL
        self.loaded = True
        logger.info("Vector store is ready (using PostgreSQL)")
    
    def add_embedded_chunks(self, embedded_chunks: List[EmbeddedChunk]) -> None:
        """Add embedded chunks to the vector store.
        
        Args:
            embedded_chunks: List of embedded chunks to add
        """
        logger.info(f"Adding {len(embedded_chunks)} embedded chunks to the vector store")
        
        for chunk in embedded_chunks:
            try:
                self.embedding_repo.create_embedding(chunk)
            except Exception as e:
                logger.error(f"Error adding embedded chunk {chunk.chunk.chunk_id}: {e}")
    
    def search(self, query_embedding: List[float], top_k: int = 5, 
               filter_dict: Optional[Dict[str, Any]] = None) -> List[RelevantChunk]:
        """Search for the most similar chunks to a query embedding.
        
        Args:
            query_embedding: Query embedding
            top_k: Number of results to return
            filter_dict: Dictionary of filters to apply
            
        Returns:
            List of relevant chunks
        """
        logger.info(f"Searching for similar chunks (top_k={top_k})")
        
        # Search for similar chunks
        results = self.embedding_repo.search_embeddings(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_dict=filter_dict
        )
        
        # Convert to RelevantChunk objects
        relevant_chunks = []
        for chunk, similarity in results:
            document_chunk = self.chunk_repo.to_model(chunk)
            relevant_chunk = RelevantChunk(
                chunk=document_chunk,
                relevance_score=float(similarity)
            )
            relevant_chunks.append(relevant_chunk)
        
        return relevant_chunks
    
    def _cosine_similarity(self, query_embedding: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
        """Calculate cosine similarity between a query embedding and all embeddings.
        
        This is not used with PostgreSQL as similarity is calculated in the database.
        """
        # This is kept for backward compatibility
        # In PostgreSQL, similarity is calculated using the cosine_similarity function
        return np.zeros(0)
    
    def _apply_filters(self, filter_dict: Dict[str, Any]) -> List[int]:
        """Apply filters to the chunks and return indices of matching chunks.
        
        This is not used with PostgreSQL as filtering is done in the database.
        """
        # This is kept for backward compatibility
        # In PostgreSQL, filtering is done in the SQL query
        return []
    
    def __del__(self):
        """Close the database session when the object is deleted."""
        if hasattr(self, 'db'):
            self.db.close() 