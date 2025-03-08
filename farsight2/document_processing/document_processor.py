"""Document processor for extracting content from 10-K/10-Q filings."""

import logging
import re
from typing import List, Optional
from datetime import datetime
import os
import json

from farsight2.models.models import (
    DocumentMetadata, 
    ParsedDocument, 
    TextChunk, 
    Table, 
    Chart
)

from farsight2.database.db import SessionLocal
from farsight2.database.repository import (
    DocumentRepository,
    TextChunkRepository,
    TableRepository,
    ChartRepository
)

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Processor for extracting content from 10-K/10-Q filings."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the document processor.
        
        Args:
            output_dir: Directory to save processed documents
        """
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "../../data/processed")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def process_filing(self, file_path: str, metadata: DocumentMetadata) -> ParsedDocument:
        """Process a filing and extract its content.
        
        Args:
            file_path: Path to the filing file
            metadata: Metadata for the filing
            
        Returns:
            ParsedDocument containing the extracted content
        """
        logger.info(f"Processing filing: {file_path}")
        
        # Read the file content
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Extract filing date if not already set
        if metadata.filing_date is None:
            metadata.filing_date = self._extract_filing_date(content)
        
        # Extract text chunks
        text_chunks = self._extract_text_chunks(content, metadata.document_id)
        
        # Extract tables
        tables = self._extract_tables(content, metadata.document_id)
        
        # Extract charts
        charts = self._extract_charts(content, metadata.document_id)
        
        # Create parsed document
        parsed_document = ParsedDocument(
            document_id=metadata.document_id,
            metadata=metadata,
            text_chunks=text_chunks,
            tables=tables,
            charts=charts
        )
        
        # Save the parsed document
        self._save_parsed_document(parsed_document)
        
        # Save to database
        self._save_to_database(parsed_document)
        
        return parsed_document
    
    def _extract_filing_date(self, content: str) -> datetime:
        """Extract the filing date from the document content."""
        # This is a simplified implementation
        # In a real implementation, you would use more robust parsing
        date_pattern = r"FILED\s*:\s*(\w+)\s+(\d+),\s+(\d{4})"
        match = re.search(date_pattern, content)
        
        if match:
            month, day, year = match.groups()
            try:
                return datetime.strptime(f"{month} {day} {year}", "%B %d %Y")
            except ValueError:
                pass
        
        # Fallback to current date if extraction fails
        logger.warning("Could not extract filing date, using current date")
        return datetime.now()
    
    def _extract_text_chunks(self, content: str, document_id: str) -> List[TextChunk]:
        """Extract text chunks from the document content."""
        # This is a simplified implementation
        # In a real implementation, you would use more sophisticated text extraction
        
        # Split content into sections based on headers
        sections = re.split(r'(ITEM\s+\d+\..*?)(?=ITEM\s+\d+\.|\Z)', content, flags=re.IGNORECASE)
        
        text_chunks = []
        for i in range(0, len(sections) - 1, 2):
            if i + 1 < len(sections):
                header = sections[i].strip()
                body = sections[i + 1].strip()
                
                if header and body:
                    chunk_id = f"{document_id}_text_{i//2}"
                    text_chunks.append(TextChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        text=body,
                        section=header,
                        page_number=None  # Would require PDF parsing to get page numbers
                    ))
        
        return text_chunks
    
    def _extract_tables(self, content: str, document_id: str) -> List[Table]:
        """Extract tables from the document content."""
        # This is a placeholder implementation
        # In a real implementation, you would use a table extraction library
        
        # Simple regex to find potential tables
        table_pattern = r'<TABLE.*?>(.*?)</TABLE>'
        matches = re.finditer(table_pattern, content, re.DOTALL | re.IGNORECASE)
        
        tables = []
        for i, match in enumerate(matches):
            table_content = match.group(1)
            chunk_id = f"{document_id}_table_{i}"
            
            # Find the nearest section header
            section = "Unknown"
            pos = match.start()
            section_match = re.search(r'(ITEM\s+\d+\..*?)(?=\n)', content[:pos], re.IGNORECASE)
            if section_match:
                section = section_match.group(1).strip()
            
            tables.append(Table(
                chunk_id=chunk_id,
                document_id=document_id,
                table_html=table_content,
                table_data=None,  # Would require parsing the HTML to extract structured data
                caption=None,
                section=section,
                page_number=None
            ))
        
        return tables
    
    def _extract_charts(self, content: str, document_id: str) -> List[Chart]:
        """Extract charts from the document content."""
        # This is a placeholder implementation
        # In a real implementation, you would need to extract images and analyze them
        
        # For now, we'll return an empty list
        return []
    
    def _save_parsed_document(self, parsed_document: ParsedDocument) -> None:
        """Save the parsed document to disk."""
        # Create a filename based on the document metadata
        metadata = parsed_document.metadata
        filename = f"{metadata.ticker}_{metadata.filing_type}_{metadata.year}"
        if metadata.quarter:
            filename += f"_Q{metadata.quarter}"
        filename += ".json"
        
        file_path = os.path.join(self.output_dir, filename)
        
        # Convert the parsed document to a dictionary
        document_dict = {
            "document_id": parsed_document.document_id,
            "metadata": {
                "document_id": metadata.document_id,
                "ticker": metadata.ticker,
                "year": metadata.year,
                "quarter": metadata.quarter,
                "filing_type": metadata.filing_type,
                "filing_date": metadata.filing_date.isoformat() if metadata.filing_date else None
            },
            "text_chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "text": chunk.text,
                    "section": chunk.section,
                    "page_number": chunk.page_number
                }
                for chunk in parsed_document.text_chunks
            ],
            "tables": [
                {
                    "chunk_id": table.chunk_id,
                    "document_id": table.document_id,
                    "table_html": table.table_html,
                    "caption": table.caption,
                    "section": table.section,
                    "page_number": table.page_number
                }
                for table in parsed_document.tables
            ],
            "charts": [
                {
                    "chunk_id": chart.chunk_id,
                    "document_id": chart.document_id,
                    "chart_data": chart.chart_data,
                    "caption": chart.caption,
                    "section": chart.section,
                    "page_number": chart.page_number
                }
                for chart in parsed_document.charts
            ]
        }
        
        # Save the document as JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(document_dict, f, indent=2)
    
    def _save_to_database(self, parsed_document: ParsedDocument) -> None:
        """Save the parsed document to the database.
        
        Args:
            parsed_document: Parsed document to save
        """
        try:
            # Create a database session
            db = SessionLocal()
            
            # Create repositories
            document_repo = DocumentRepository(db)
            text_chunk_repo = TextChunkRepository(db)
            table_repo = TableRepository(db)
            chart_repo = ChartRepository(db)
            
            # Save document metadata
            document_repo.create_document(parsed_document.metadata)
            
            # Save text chunks
            for text_chunk in parsed_document.text_chunks:
                text_chunk_repo.create_text_chunk(text_chunk)
            
            # Save tables
            for table in parsed_document.tables:
                table_repo.create_table(table)
            
            # Save charts
            for chart in parsed_document.charts:
                chart_repo.create_chart(chart)
            
            # Close the session
            db.close()
            
            logger.info(f"Saved document {parsed_document.document_id} to database")
        except Exception as e:
            logger.error(f"Error saving document to database: {e}") 