"""Mock data for testing."""

from datetime import datetime

from farsight2.models.models import (
    DocumentMetadata,
    DocumentChunk,
    TextChunk,
    Table,
    Chart,
    ParsedDocument
)


def create_mock_document():
    """Create a mock document for testing."""
    return DocumentMetadata(
        document_id="DOC123",
        ticker="AAPL",
        year=2023,
        quarter=None,
        filing_type="10-K",
        filing_date=datetime(2023, 12, 31)
    )


def create_mock_document_chunk():
    """Create a mock document chunk for testing."""
    return DocumentChunk(
        chunk_id="CHUNK1",
        document_id="DOC123",
        content="Test content for the document chunk.",
        content_type="text",
        location="Section 1"
    )


def create_mock_text_chunk():
    """Create a mock text chunk for testing."""
    return TextChunk(
        chunk_id="TEXT1",
        document_id="DOC123",
        text="Test text content.",
        section="Section 1",
        page_number=1
    )


def create_mock_table():
    """Create a mock table for testing."""
    return Table(
        chunk_id="TABLE1",
        document_id="DOC123",
        table_html="<table><tr><td>Data</td></tr></table>",
        table_data=[["Data"]],
        caption="Test Table",
        section="Section 2",
        page_number=2
    )


def create_mock_chart():
    """Create a mock chart for testing."""
    return Chart(
        chunk_id="CHART1",
        document_id="DOC123",
        chart_data={"type": "bar", "data": [1, 2, 3]},
        caption="Test Chart",
        section="Section 3",
        page_number=3
    )


def create_mock_parsed_document():
    """Create a mock parsed document with all components."""
    return ParsedDocument(
        document_id="DOC123",
        text_chunks=[create_mock_text_chunk()],
        tables=[create_mock_table()],
        charts=[create_mock_chart()]
    )


def create_mock_html_content():
    """Create mock HTML content for testing document processing."""
    return """
    <html>
    <head><title>Test Document</title></head>
    <body>
        <h1>ITEM 1. BUSINESS</h1>
        <p>Apple Inc. is a technology company that designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories.</p>
        
        <h1>ITEM 1A. RISK FACTORS</h1>
        <p>The Company's business, operating results, and financial condition are subject to various risks and uncertainties.</p>
        
        <h1>ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS</h1>
        <p>The Company's fiscal year 2023 was a challenging year with revenues of $394.3 billion, down 3% from 2022.</p>
        
        <table>
            <tr><th>Year</th><th>Revenue ($ billions)</th></tr>
            <tr><td>2023</td><td>394.3</td></tr>
            <tr><td>2022</td><td>407.1</td></tr>
            <tr><td>2021</td><td>378.2</td></tr>
        </table>
    </body>
    </html>
    """


def create_mock_test_suite():
    """Create a mock test suite for evaluation testing."""
    return {
        "name": "AAPL_2023",
        "questions": [
            "What was Apple's revenue in 2023?",
            "What are the main risk factors for Apple?",
            "How did Apple's revenue change from 2022 to 2023?"
        ],
        "expected_answers": [
            "Apple's revenue in 2023 was $394.3 billion.",
            "Apple's business, operating results, and financial condition are subject to various risks and uncertainties.",
            "Apple's revenue decreased by 3% from 2022 to 2023."
        ]
    } 