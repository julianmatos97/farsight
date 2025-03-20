"""Response generator for generating responses based on relevant content."""

import logging
import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple

from openai import OpenAI

from farsight2.models.models import (
    Fact,
    RelevantChunk,
    Citation,
    FormattedResponse,
    FactValue,
)

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generator for creating responses based on relevant content."""

    def __init__(
        self, api_key: Optional[str] = None
    ):
        """Initialize the response generator.

        Args:
            document_metadata_store: Dictionary mapping document IDs to metadata
            api_key: OpenAI API key
        """
        logger.info("Initializing ResponseGenerator")

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OpenAI API key not provided")
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)
        logger.debug("OpenAI client initialized")

        # Default model for response generation
        self.model = "gpt-4o"
        logger.info(f"Using model: {self.model}")

    def generate_response(
        self,
        query: str,
        relevant_chunks: List[RelevantChunk],
        relevant_fact_values: Optional[List[Tuple[FactValue, str]]] = None,
    ) -> FormattedResponse:
        """Generate a response based on relevant content.

        Args:
            query: User query
            relevant_chunks: List of relevant document chunks
            relevant_facts: List of relevant XBRL facts
            fact_values: List of fact values for the relevant facts

        Returns:
            Formatted response with citations
        """
        logger.info(f"Generating response for query: {query}")
        logger.info(f"Number of relevant chunks: {len(relevant_chunks)}")
        logger.info(
            f"Number of relevant fact values: {len(relevant_fact_values) if relevant_fact_values else 0}"
        )

        # Prepare context from document chunks
        chunk_context = []
        for chunk in relevant_chunks:  # type: RelevantChunk
            metadata = {}
            context = {
                "content": chunk.chunk.content[:10_000],
                "content_type": chunk.chunk.content_type,
                "location": chunk.chunk.location,
                "document_id": chunk.chunk.document_id,
                "filing_type": metadata.get("filing_type"),
                "company": metadata.get("ticker"),
                "year": metadata.get("year"),
                "quarter": metadata.get("quarter"),
            }
            chunk_context.append(context)
        logger.debug(f"Prepared {len(chunk_context)} document chunks for context")

        # Prepare context from XBRL facts
        fact_context = []


        if relevant_fact_values:
            for fact_value, description in relevant_fact_values:  # type: Tuple[FactValue, str]
                
                logger.debug(f"Processing fact value: {fact_value.fact_id}")
                fact_info = {
                    "fact_id": fact_value.fact_id,
                    "values": [
                        {
                            "value": fact_value.value,
                            "fiscal_year": fact_value.fiscal_year,
                            "fiscal_period": fact_value.fiscal_period,
                            "document_id": fact_value.document_id,
                            "ticker": fact_value.ticker,
                        }
                    ],
                    "description": description,
                }
                fact_context.append(fact_info)
            logger.debug(f"Prepared {len(fact_context)} fact values for context")

        # Create prompt for the LLM
        logger.debug("Creating prompt for LLM")
        prompt = f"""
        Answer the following question about company financial filings using the provided context.
        
        Question: {query}
        
        Document Context:
        {json.dumps(chunk_context, indent=2)}
        
        Facts Values:
        {json.dumps(fact_context, indent=2) if fact_context else "No relevant Fact Values facts found."}
        
        Instructions:
        1. Answer the question accurately using only the provided context
        2. Cite specific sources for each piece of information
        3. If using numerical data, specify the source (document text vs Fact Value)
        4. If information appears in both document text and Fact Values, prefer Fact Values
        5. Format tables and numerical data clearly
        6. Indicate if any part of the question cannot be answered with the available context
        
        Format your response as follows:
        ANSWER: Your detailed answer here
        
        SOURCES:
        [1] Description of source 1 with document ID/fact ID and location
        [2] Description of source 2 with document ID/fact ID and location
        ...
        """

        # Generate response using the LLM
        try:
            logger.info("Sending request to OpenAI API")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analysis assistant that provides accurate, well-cited answers about company financial filings.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,  # Low temperature for more factual responses
            )
            logger.debug("Received response from OpenAI API")

            # Parse the response
            content = response.choices[0].message.content
            logger.info(f"Response: {content}")
            answer_part, sources_part = self._parse_response(content)
            logger.debug("Successfully parsed response into answer and sources")

            # Create citations from sources
            logger.debug("Creating citations from sources")
            citations = self._create_citations(
                sources_part, chunk_context, fact_context
            )
            logger.info(f"Created {len(citations)} citations")

            return FormattedResponse(response=answer_part.strip(), citations=citations)

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def _parse_response(self, content: str) -> Tuple[str, str]:
        """Parse the LLM response into answer and sources parts."""
        logger.debug("Parsing LLM response")
        parts = content.split("SOURCES:")
        if len(parts) != 2:
            logger.error(
                "Response format error: Could not split into answer and sources"
            )
            raise ValueError("Response not in expected format")

        answer = parts[0].replace("ANSWER:", "").strip()
        sources = parts[1].strip()
        logger.debug(f"Parsed answer length: {len(answer)} characters")
        logger.debug(f"Parsed sources length: {len(sources)} characters")

        return answer, sources

    def _create_citations(
        self,
        sources: str,
        chunk_context: List[Dict[str, Any]],
        fact_context: List[Dict[str, Any]],
    ) -> List[Citation]:
        """Create citation objects from source descriptions."""
        logger.debug("Creating citations from source descriptions")
        citations = []

        # Parse source entries (format: [n] description)
        source_entries = re.findall(r"\[\d+\](.*?)(?=\[\d+\]|\Z)", sources, re.DOTALL)
        logger.debug(f"Found {len(source_entries)} source entries")

        for i, entry in enumerate(source_entries):
            entry = entry.strip()
            logger.debug(f"Processing source entry {i + 1}: {entry[:50]}...")

            # Try to match with document chunks
            chunk_matched = False
            for chunk in chunk_context:
                if chunk["document_id"] in entry:
                    logger.debug(
                        f"Matched entry with document chunk: {chunk['document_id']}"
                    )
                    citations.append(
                        Citation(
                            document_id=chunk["document_id"],
                            filing_type=chunk["filing_type"],
                            company=chunk["company"],
                            year=chunk["year"],
                            quarter=chunk["quarter"],
                            location=chunk["location"],
                            content=chunk["content"],
                            content_type=chunk["content_type"],
                        )
                    )
                    chunk_matched = True

            # Try to match with XBRL facts
            fact_matched = False
            for fact in fact_context:
                print(fact)
                if fact["fact_id"] in entry:
                    # Create a citation for each value of the fact
                    for value in fact["values"]:
                        citations.append(
                            Citation(
                                document_id=value["document_id"],
                                filing_type="Fact Value",
                                company=value.get("ticker", "Unknown"),
                                year=value["fiscal_year"],
                                quarter=None,
                                location=f"",
                                content=f"{value['value']}",
                                content_type="fact_value",
                                fact_id=fact.get("fact_id", "Unknown"),
                            )
                        )
                    fact_matched = True

            if not (chunk_matched or fact_matched):
                logger.warning(
                    f"Could not match source entry to any document or fact: {entry[:100]}..."
                )

        return citations
