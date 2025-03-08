"""Response generator for generating responses based on relevant content."""

import logging
import os
import json
from typing import List, Dict, Any, Optional, Tuple

from openai import OpenAI

from farsight2.models.models import (
    RelevantChunk,
    Citation,
    FormattedResponse
)

logger = logging.getLogger(__name__)

class ResponseGenerator:
    """Generator for creating responses based on relevant content."""
    
    def __init__(self, document_metadata_store: Dict[str, Any], api_key: Optional[str] = None):
        """Initialize the response generator.
        
        Args:
            document_metadata_store: Dictionary mapping document IDs to metadata
            api_key: OpenAI API key
        """
        self.document_metadata_store = document_metadata_store
        
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        
        # Default model for response generation
        self.model = "gpt-4o"
    
    def generate_response(self, query: str, relevant_chunks: List[RelevantChunk]) -> FormattedResponse:
        """Generate a response based on relevant chunks.
        
        Args:
            query: Original query
            relevant_chunks: List of relevant chunks
            
        Returns:
            Formatted response with citations
        """
        logger.info(f"Generating response for query: {query}")
        
        # Prepare the context from relevant chunks
        context = self._prepare_context(relevant_chunks)
        
        # Generate the response using the LLM
        response_text, citation_indices = self._generate_response_with_citations(query, context)
        
        # Create citations
        citations = self._create_citations(relevant_chunks, citation_indices)
        
        # Create formatted response
        formatted_response = FormattedResponse(
            response=response_text,
            citations=citations
        )
        
        return formatted_response
    
    def _prepare_context(self, relevant_chunks: List[RelevantChunk]) -> List[Dict[str, Any]]:
        """Prepare the context from relevant chunks for the LLM."""
        context = []
        
        for i, chunk in enumerate(relevant_chunks):
            # Get document metadata
            document_id = chunk.chunk.document_id
            metadata = self.document_metadata_store.get(document_id, {})
            
            # Create context entry
            context_entry = {
                "index": i + 1,  # 1-based index for the LLM
                "document_id": document_id,
                "content_type": chunk.chunk.content_type,
                "location": chunk.chunk.location,
                "content": chunk.chunk.content,
                "company": metadata.get("ticker", "Unknown"),
                "filing_type": metadata.get("filing_type", "Unknown"),
                "year": metadata.get("year", 0),
                "quarter": metadata.get("quarter")
            }
            
            context.append(context_entry)
        
        return context
    
    def _generate_response_with_citations(self, query: str, context: List[Dict[str, Any]]) -> Tuple[str, Dict[int, List[int]]]:
        """Generate a response with citations using the LLM."""
        try:
            # Prepare the context for the prompt
            context_text = ""
            for entry in context:
                context_text += f"[{entry['index']}] "
                context_text += f"Company: {entry['company']}, "
                context_text += f"Filing: {entry['filing_type']}, "
                context_text += f"Year: {entry['year']}"
                if entry['quarter']:
                    context_text += f", Quarter: {entry['quarter']}"
                context_text += f"\nLocation: {entry['location']}\n"
                context_text += f"Content: {entry['content'][:1000]}...\n\n"  # Truncate for brevity
            
            # Create the prompt
            prompt = f"""
            You are a financial analysis assistant that answers questions about company financial filings (10-K/10-Q).
            
            Please answer the following query based on the provided context. Your answer should be accurate, concise, and based only on the information in the context.
            
            Query: {query}
            
            Context:
            {context_text}
            
            When referring to information from the context, cite your sources using the format [X], where X is the index of the context entry.
            
            For example: "According to the 2022 annual report, revenue increased by 15% [3]."
            
            If the context doesn't contain enough information to answer the query, say so clearly.
            
            Your response should be in this format:
            1. A direct answer to the query
            2. Any relevant supporting details
            3. Citations for all factual claims
            
            Respond in JSON format with these fields:
            - "response": your complete response text with citations
            - "citations": a dictionary mapping paragraph numbers (1-based) to lists of context indices used in that paragraph
            """
            
            # Call the LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial analysis assistant that answers questions about company financial filings."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Extract the response and citations
            response_text = result.get("response", "")
            citation_indices = result.get("citations", {})
            
            # Convert citation indices from strings to integers
            citation_indices_int = {}
            for para_num_str, indices in citation_indices.items():
                try:
                    para_num = int(para_num_str)
                    citation_indices_int[para_num] = indices
                except ValueError:
                    pass
            
            return response_text, citation_indices_int
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"I apologize, but I encountered an error while generating a response: {str(e)}", {}
    
    def _create_citations(self, relevant_chunks: List[RelevantChunk], citation_indices: Dict[int, List[int]]) -> List[Citation]:
        """Create citations from relevant chunks and citation indices."""
        citations = []
        
        # Flatten the citation indices
        all_indices = []
        for indices in citation_indices.values():
            all_indices.extend(indices)
        
        # Remove duplicates and sort
        all_indices = sorted(set(all_indices))
        
        # Create citations for each cited chunk
        for index in all_indices:
            # Adjust for 1-based indexing
            chunk_index = index - 1
            
            if 0 <= chunk_index < len(relevant_chunks):
                chunk = relevant_chunks[chunk_index]
                document_id = chunk.chunk.document_id
                
                # Get document metadata
                metadata = self.document_metadata_store.get(document_id, {})
                
                # Create citation
                citation = Citation(
                    document_id=document_id,
                    filing_type=metadata.get("filing_type", "Unknown"),
                    company=metadata.get("ticker", "Unknown"),
                    year=metadata.get("year", 0),
                    quarter=metadata.get("quarter"),
                    location=chunk.chunk.location,
                    content=chunk.chunk.content[:200] + "..."  # Truncate for brevity
                )
                
                citations.append(citation)
        
        return citations 