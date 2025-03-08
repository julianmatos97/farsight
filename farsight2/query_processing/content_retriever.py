"""Content retriever for finding the most relevant chunks for a query."""

import logging
import os
import json
from typing import List, Optional

from openai import OpenAI

from farsight2.models.models import (
    QueryAnalysis,
    DocumentReference,
    RelevantChunk
)
from farsight2.vector_store.vector_store import VectorStore
from farsight2.embedding.embedder import Embedder

logger = logging.getLogger(__name__)

class ContentRetriever:
    """Retriever for finding the most relevant chunks for a query."""
    
    def __init__(self, vector_store: VectorStore, embedder: Embedder, api_key: Optional[str] = None):
        """Initialize the content retriever.
        
        Args:
            vector_store: Vector store containing document chunk embeddings
            embedder: Embedder for generating query embeddings
            api_key: OpenAI API key
        """
        self.vector_store = vector_store
        self.embedder = embedder
        
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        
        # Default model for reranking
        self.model = "gpt-4o"
    
    def retrieve_content(self, query: str, query_analysis: QueryAnalysis, 
                         document_references: List[DocumentReference], 
                         top_k: int = 10) -> List[RelevantChunk]:
        """Retrieve the most relevant chunks for a query.
        
        Args:
            query: Original query
            query_analysis: Analysis of the query
            document_references: List of document references
            top_k: Number of chunks to retrieve
            
        Returns:
            List of relevant chunks
        """
        logger.info(f"Retrieving content for query: {query}")
        
        # Generate embedding for the query
        query_embedding = self._generate_query_embedding(query)
        
        # Get document IDs from references
        document_ids = [ref.document_id for ref in document_references]
        
        # Retrieve relevant chunks from the vector store
        all_chunks = []
        for doc_id in document_ids:
            # Search the vector store for chunks from this document
            filter_dict = {"document_id": doc_id}
            chunks = self.vector_store.search(query_embedding, top_k=5, filter_dict=filter_dict)
            all_chunks.extend(chunks)
        
        # Sort by relevance score
        all_chunks.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Take the top k chunks
        top_chunks = all_chunks[:top_k]
        
        # Rerank the chunks using the LLM if we have more than a few
        if len(top_chunks) > 3:
            top_chunks = self._rerank_chunks(query, top_chunks)
        
        return top_chunks
    
    def _generate_query_embedding(self, query: str) -> List[float]:
        """Generate an embedding for a query."""
        # Use the embedder to generate the embedding
        # This is a simplified implementation
        # In a real implementation, you would use the embedder's API
        
        # Create a dummy document chunk for the query
        dummy_chunk = {
            "content": query,
            "content_type": "query"
        }
        
        # Generate embedding
        embedding = self.embedder._generate_embedding(query)
        
        return embedding
    
    def _rerank_chunks(self, query: str, chunks: List[RelevantChunk]) -> List[RelevantChunk]:
        """Rerank chunks using an LLM to better match the query intent."""
        try:
            # Prepare the chunks for reranking
            chunk_texts = []
            for i, chunk in enumerate(chunks):
                chunk_text = f"Chunk {i+1}:\n"
                chunk_text += f"Type: {chunk.chunk.content_type}\n"
                chunk_text += f"Location: {chunk.chunk.location}\n"
                chunk_text += f"Content: {chunk.chunk.content[:500]}...\n"  # Truncate for brevity
                chunk_texts.append(chunk_text)
            
            # Create the prompt
            prompt = f"""
            I need you to rerank these document chunks based on their relevance to the following query:
            
            Query: {query}
            
            Here are the chunks:
            
            {'\n'.join(chunk_texts)}
            
            Please provide a JSON array of integers representing the indices of the chunks in order of relevance,
            from most relevant to least relevant. The indices should be 1-based (i.e., the first chunk is 1, not 0).
            
            For example: [3, 1, 5, 2, 4] means chunk 3 is most relevant, followed by chunk 1, etc.
            """
            
            # Call the LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial analysis assistant that helps rank document chunks by relevance to a query."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            content = response.choices[0].message.content
            ranking = json.loads(content)
            
            # Get the ranking
            if isinstance(ranking, dict) and "ranking" in ranking:
                indices = ranking["ranking"]
            elif isinstance(ranking, list):
                indices = ranking
            else:
                logger.warning("Invalid ranking format from LLM")
                return chunks
            
            # Convert to 0-based indices
            indices = [i-1 for i in indices if 1 <= i <= len(chunks)]
            
            # Rerank the chunks
            reranked_chunks = []
            for i in indices:
                if i < len(chunks):
                    # Update the relevance score based on the new ranking
                    chunk = chunks[i]
                    chunk.relevance_score = 1.0 - (indices.index(i) / len(indices))
                    reranked_chunks.append(chunk)
            
            # Add any chunks that weren't ranked
            ranked_indices = set(indices)
            for i, chunk in enumerate(chunks):
                if i not in ranked_indices and len(reranked_chunks) < len(chunks):
                    chunk.relevance_score = 0.0  # Lowest relevance
                    reranked_chunks.append(chunk)
            
            return reranked_chunks
        except Exception as e:
            logger.error(f"Error reranking chunks: {e}")
            return chunks 