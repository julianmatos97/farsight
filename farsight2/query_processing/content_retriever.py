"""Content retriever for finding the most relevant chunks for a query."""

import logging
import json
import os
from typing import List

from openai import OpenAI


from farsight2.models.models import QueryAnalysis, DocumentReference, RelevantChunk
from farsight2.embedding.unified_embedding_service import UnifiedEmbeddingService
from farsight2.database.unified_repository import UnifiedRepository

logger = logging.getLogger(__name__)


class ContentRetriever:
    """Retriever for finding the most relevant chunks for a query."""

    def __init__(self, embedding_service=None, repository=None):
        """Initialize the content retriever.

        Args:
            embedding_service: Unified embedding service for generating query embeddings
            repository: Repository for database access
        """
        self.repository = repository or UnifiedRepository()
        self.embedding_service = embedding_service or UnifiedEmbeddingService(
            repository=self.repository
        )
        self.client = OpenAI(
            api_key="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"
        )
        # Default model for reranking
        self.model = "gpt-4o"

    def retrieve_content(
        self,
        query: str,
        query_analysis: QueryAnalysis,
        document_references: List[DocumentReference],
        top_k: int = 3,
    ) -> List[RelevantChunk]:
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

        # Retrieve relevant chunks from the unified embedding service
        relevant_chunks = self.embedding_service.search_documents(
            query, document_references, top_k
        )

        # Sort by relevance score
        relevant_chunks.sort(key=lambda x: x.relevance_score, reverse=True)

        # Take the top k chunks
        top_chunks = relevant_chunks[:top_k]

        # Rerank the chunks using the LLM if we have more than a few
        # if len(top_chunks) > 3:
        #     top_chunks = self._rerank_chunks(query, top_chunks)

        return top_chunks

    def _rerank_chunks(
        self, query: str, chunks: List[RelevantChunk]
    ) -> List[RelevantChunk]:
        """Rerank chunks using an LLM to better match the query intent."""
        try:
            # Prepare the chunks for reranking
            chunk_texts = []
            for i, chunk in enumerate(chunks):
                chunk_text = f"Chunk {i + 1}:\n"
                chunk_text += f"Type: {chunk.chunk.content_type}\n"
                chunk_text += f"Location: {chunk.chunk.location}\n"
                chunk_text += (
                    f"Content: {chunk.chunk.content[:500]}...\n"  # Truncate for brevity
                )
                chunk_texts.append(chunk_text)

            # Create a more detailed prompt for better reranking
            prompt = f"""
            I need you to rerank these document chunks based on their relevance to the following query:
            
            Query: {query}
            
            When evaluating relevance, consider:
            1. Direct answers to the query
            2. Contextual information that helps understand the answer
            3. Financial data that supports the query's intent
            4. Recency and specificity of information
            
            Here are the chunks:
            
            {"\n".join(chunk_texts)}
            
            Please provide a JSON object with a "ranking" key containing an array of integers representing 
            the indices of the chunks in order of relevance, from most relevant to least relevant.
            The indices should be 1-based (i.e., the first chunk is 1, not 0).
            
            Also include a "reasoning" key with a brief explanation of your ranking decision.
            
            Example response:
            {{
                "ranking": [3, 1, 5, 2, 4],
                "reasoning": "Chunk 3 directly answers the query about revenue growth, while chunk 1 provides important context..."
            }}
            """

            # Call the LLM with temperature adjustment for more consistent ranking
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analysis assistant that helps rank document chunks by relevance to a query. Focus on financial metrics, company performance, and specific data points that answer the query.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,  # Lower temperature for more consistent ranking
            )

            # Parse the response with error handling
            try:
                content = response.choices[0].message.content
                ranking_data = json.loads(content)

                # Get the ranking with improved validation
                if isinstance(ranking_data, dict) and "ranking" in ranking_data:
                    indices = ranking_data["ranking"]
                    # Log reasoning if available
                    if "reasoning" in ranking_data:
                        logger.info(f"Reranking reasoning: {ranking_data['reasoning']}")
                elif isinstance(ranking_data, list):
                    indices = ranking_data
                    logger.warning(
                        "Ranking returned as list instead of object with 'ranking' key"
                    )
                else:
                    logger.warning(f"Invalid ranking format from LLM: {content}")
                    return chunks
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                return chunks
            # Convert to 0-based indices
            indices = [i - 1 for i in indices if 1 <= i <= len(chunks)]

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
