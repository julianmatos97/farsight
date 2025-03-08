"""Query analyzer for extracting key information from queries."""

import logging
import re
import os
import json
from typing import List, Dict, Optional
from datetime import datetime

from openai import OpenAI

from farsight2.models.models import QueryAnalysis

logger = logging.getLogger(__name__)

class QueryAnalyzer:
    """Analyzer for extracting key information from queries."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the query analyzer.
        
        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        
        # Default model for query analysis
        self.model = "gpt-4o"
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze a query to extract key information.
        
        Args:
            query: Query to analyze
            
        Returns:
            QueryAnalysis containing extracted information
        """
        logger.info(f"Analyzing query: {query}")
        
        # Use a simple regex-based approach for basic queries
        companies = self._extract_companies(query)
        years = self._extract_years(query)
        quarters = self._extract_quarters(query)
        
        # For more complex queries, use LLM-based extraction
        if not companies or not years:
            llm_analysis = self._llm_analyze_query(query)
            
            # Merge results, preferring regex results when available
            if not companies:
                companies = llm_analysis.get("companies", [])
            if not years:
                years = llm_analysis.get("years", [])
            if not quarters:
                quarters = llm_analysis.get("quarters", [])
            
            topics = llm_analysis.get("topics", [])
        else:
            # For simple queries, extract topics using regex
            topics = self._extract_topics(query)
        
        return QueryAnalysis(
            companies=companies,
            years=years,
            quarters=quarters,
            topics=topics
        )
    
    def _extract_companies(self, query: str) -> List[str]:
        """Extract company names or tickers from a query using regex."""
        # This is a simplified implementation
        # In a real implementation, you would use a more robust approach
        
        # Look for common company name patterns
        company_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*|[A-Z]{2,5})\b'
        matches = re.findall(company_pattern, query)
        
        # Filter out common words that might be matched
        common_words = {"THE", "AND", "FOR", "IN", "ON", "AT", "BY", "TO", "FROM", "WITH"}
        companies = [match for match in matches if match.upper() not in common_words]
        
        return companies
    
    def _extract_years(self, query: str) -> List[int]:
        """Extract years from a query using regex."""
        # Look for 4-digit years
        year_pattern = r'\b(20\d{2})\b'
        matches = re.findall(year_pattern, query)
        
        # Convert to integers
        years = [int(match) for match in matches]
        
        # If no years found, try to infer from relative terms
        if not years:
            current_year = datetime.now().year
            
            if re.search(r'\blast\s+year\b', query, re.IGNORECASE):
                years.append(current_year - 1)
            elif re.search(r'\bthis\s+year\b', query, re.IGNORECASE):
                years.append(current_year)
            elif re.search(r'\bnext\s+year\b', query, re.IGNORECASE):
                years.append(current_year + 1)
        
        return years
    
    def _extract_quarters(self, query: str) -> List[int]:
        """Extract quarters from a query using regex."""
        # Look for quarter references
        quarter_pattern = r'\bQ([1-4])\b'
        matches = re.findall(quarter_pattern, query, re.IGNORECASE)
        
        # Convert to integers
        quarters = [int(match) for match in matches]
        
        return quarters
    
    def _extract_topics(self, query: str) -> List[str]:
        """Extract topics from a query using regex."""
        # This is a simplified implementation
        # In a real implementation, you would use a more robust approach
        
        # Define common financial topics
        financial_topics = {
            "revenue": ["revenue", "sales", "income"],
            "profit": ["profit", "earnings", "net income", "ebitda"],
            "growth": ["growth", "increase", "decrease", "change"],
            "expenses": ["expenses", "costs", "spending"],
            "assets": ["assets", "liabilities", "equity", "balance sheet"],
            "cash flow": ["cash flow", "cash", "liquidity"],
            "debt": ["debt", "loans", "borrowing"],
            "dividend": ["dividend", "payout", "yield"],
            "investment": ["investment", "capex", "capital expenditure"],
            "risk": ["risk", "uncertainty", "exposure"]
        }
        
        # Look for topics in the query
        topics = []
        query_lower = query.lower()
        
        for topic, keywords in financial_topics.items():
            for keyword in keywords:
                if keyword in query_lower:
                    topics.append(topic)
                    break
        
        return topics
    
    def _llm_analyze_query(self, query: str) -> Dict[str, List]:
        """Analyze a query using an LLM to extract key information."""
        try:
            prompt = f"""
            Analyze the following query about company financial filings (10-K/10-Q) and extract the following information:
            1. Company names or tickers mentioned
            2. Years mentioned or implied
            3. Quarters mentioned or implied (1, 2, 3, or 4)
            4. Main topics or financial metrics of interest
            
            Query: {query}
            
            Respond with a JSON object containing the following keys:
            - companies: list of company names or tickers
            - years: list of years as integers
            - quarters: list of quarters as integers
            - topics: list of main topics or financial metrics
            
            If any information is not present or cannot be inferred, provide an empty list for that key.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial analysis assistant that extracts key information from queries about company financial filings."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            content = response.choices[0].message.content
            analysis = json.loads(content)
            
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing query with LLM: {e}")
            return {
                "companies": [],
                "years": [],
                "quarters": [],
                "topics": []
            } 