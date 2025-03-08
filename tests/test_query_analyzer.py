"""Tests for the query analyzer."""

import unittest
from unittest.mock import patch, MagicMock

from farsight2.query_processing.query_analyzer import QueryAnalyzer
from farsight2.models.models import QueryAnalysis

class TestQueryAnalyzer(unittest.TestCase):
    """Tests for the QueryAnalyzer class."""
    
    @patch('farsight2.query_processing.query_analyzer.OpenAI')
    def test_extract_companies(self, mock_openai):
        """Test extracting companies from a query."""
        # Create a mock QueryAnalyzer
        analyzer = QueryAnalyzer(api_key="test-key")
        
        # Test simple company extraction
        companies = analyzer._extract_companies("What was Apple's revenue in 2023?")
        self.assertIn("Apple", companies)
        
        # Test ticker extraction
        companies = analyzer._extract_companies("What was AAPL's revenue in 2023?")
        self.assertIn("AAPL", companies)
    
    @patch('farsight2.query_processing.query_analyzer.OpenAI')
    def test_extract_years(self, mock_openai):
        """Test extracting years from a query."""
        # Create a mock QueryAnalyzer
        analyzer = QueryAnalyzer(api_key="test-key")
        
        # Test year extraction
        years = analyzer._extract_years("What was Apple's revenue in 2023?")
        self.assertIn(2023, years)
    
    @patch('farsight2.query_processing.query_analyzer.OpenAI')
    def test_extract_quarters(self, mock_openai):
        """Test extracting quarters from a query."""
        # Create a mock QueryAnalyzer
        analyzer = QueryAnalyzer(api_key="test-key")
        
        # Test quarter extraction
        quarters = analyzer._extract_quarters("What was Apple's revenue in Q2 2023?")
        self.assertIn(2, quarters)
    
    @patch('farsight2.query_processing.query_analyzer.OpenAI')
    def test_analyze_query(self, mock_openai):
        """Test analyzing a query."""
        # Create a mock response for the LLM
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"companies": ["Apple"], "years": [2023], "quarters": [], "topics": ["revenue"]}'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Create a mock QueryAnalyzer
        analyzer = QueryAnalyzer(api_key="test-key")
        
        # Mock the LLM analyze method to avoid actual API calls
        analyzer._llm_analyze_query = MagicMock(return_value={
            "companies": ["Apple"],
            "years": [2023],
            "quarters": [],
            "topics": ["revenue"]
        })
        
        # Test query analysis
        query_analysis = analyzer.analyze_query("What was Apple's revenue in 2023?")
        
        self.assertIsInstance(query_analysis, QueryAnalysis)
        self.assertIn("Apple", query_analysis.companies)
        self.assertIn(2023, query_analysis.years)
        self.assertEqual([], query_analysis.quarters)

if __name__ == '__main__':
    unittest.main() 