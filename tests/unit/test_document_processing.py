"""Unit tests for document processing."""

import os
import pytest
import tempfile
from unittest.mock import MagicMock, patch

from farsight2.document_processing.document_processor import DocumentProcessor
from farsight2.document_processing.edgar_client import EdgarClient


@patch('farsight2.document_processing.edgar_client.requests.get')
def test_edgar_client_download(mock_get):
    """Test downloading a filing with EdgarClient."""
    # Fix: Create a unique temp directory for each test
    temp_dir = tempfile.mkdtemp()
    try:
        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.content = b'<html><body>Filing content</body></html>'
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Create a client and download a filing
        client = EdgarClient(download_dir=temp_dir)
        
        # Fix: Mock methods properly with context managers
        with patch.object(client, '_format_cik', return_value='0000000000'):
            with patch.object(client, '_find_filing_url', return_value='https://example.com/filing.html'):
                # Call the method under test
                result = client.download_filing('AAPL', 2023, None, '10-K')
                
                # Verify the request was made
                assert mock_get.call_count >= 1
                # The result should be a file path
                assert isinstance(result, str)
    finally:
        # Clean up temp files
        for file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file))
        os.rmdir(temp_dir)


@patch('farsight2.document_processing.document_processor.DocumentProcessor._extract_text_chunks')
@patch('farsight2.document_processing.document_processor.DocumentProcessor._extract_tables')
@patch('farsight2.document_processing.document_processor.DocumentProcessor._extract_charts')
def test_document_processor(mock_extract_charts, mock_extract_tables, mock_extract_text, 
                           repository, embedding_service, temp_file):
    """Test processing a document."""
    # Fix: Set return values for mocked methods
    mock_extract_text.return_value = []
    mock_extract_tables.return_value = []
    mock_extract_charts.return_value = []
    
    # Create a processor
    processor = DocumentProcessor(embedding_service=embedding_service, repository=repository)
    
    # Fix: Mock repository methods with patch
    with patch.object(repository, 'get_company', return_value=None):
        with patch.object(repository, 'create_company', return_value=MagicMock(ticker="AAPL", name="Apple Inc.")):
            with patch.object(repository, 'create_document', return_value=MagicMock(
                document_id="DOC123",
                ticker="AAPL",
                year=2023,
                quarter=None,
                filing_type="10-K"
            )):
                # Fix: Parse document properly
                with patch.object(processor, '_parse_document', return_value=MagicMock(
                    document_id="DOC123",
                    text_chunks=[],
                    tables=[],
                    charts=[]
                )):
                    # Fix: Mock the EdgarClient properly
                    with patch('farsight2.document_processing.document_processor.EdgarClient') as mock_edgar:
                        mock_client = MagicMock()
                        mock_client.download_filing.return_value = temp_file
                        mock_edgar.return_value = mock_client
                        
                        # Call the method under test - fix signature if needed
                        result = processor.process_document(temp_file, "AAPL", 2023, None, "10-K")
                        
                        # Verify results
                        assert result is not None 