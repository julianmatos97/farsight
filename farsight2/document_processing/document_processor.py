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

from farsight2.embedding.unified_embedding_service import UnifiedEmbeddingService
from farsight2.database.unified_repository import UnifiedRepository

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Processor for extracting content from 10-K/10-Q filings."""
    
    def __init__(self, embedding_service=None, repository=None):
        """Initialize the document processor.
        
        Args:
            embedding_service: Unified embedding service
            repository: Unified repository
        """
        self.repository = repository or UnifiedRepository()
        self.embedding_service = embedding_service or UnifiedEmbeddingService(repository=self.repository)
        self.output_dir = os.path.join(os.path.dirname(__file__), "../../data/processed")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def process_filing(self, content: str, metadata: DocumentMetadata) -> ParsedDocument:
        """Process a filing and extract its content.
        
        Args:
            content: Content of the filing
            metadata: Metadata for the filing
            
        Returns:
            ParsedDocument containing the extracted content
        """
        
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
        """
        Extract text chunks from HTML document content.
        
        Args:
            content: HTML content of the document
            document_id: ID of the document
            
        Returns:
            List of TextChunk objects
        """
        from bs4 import BeautifulSoup
        import re
        
        # Parse HTML content
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove script and style elements that aren't relevant
        for element in soup(["script", "style", "head", "meta", "link"]):
            element.extract()
        
        # Look for common 10-K/10-Q section patterns
        text_chunks = []
        
        # Try to find sections based on SEC's common structure
        # Method 1: Look for heading elements with ITEM patterns
        item_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'div', 'p', 'section' ], 
                                     string=re.compile(r'^\s*ITEM\s+\d+', re.IGNORECASE))
        
        # If we found item headings, extract content between them
        if item_headings:
            logger.info(f"Found {len(item_headings)} SEC item headings")
            
            for i, heading in enumerate(item_headings):
                # Get section title from the heading
                section_title = heading.get_text().strip()
                
                # Get all content until the next heading or end
                content_elements = []
                current = heading.next_sibling
                
                # If this is the last heading, collect all remaining siblings
                if i == len(item_headings) - 1:
                    while current:
                        if current.name and current.get_text().strip():
                            content_elements.append(current)
                        current = current.next_sibling
                else:
                    # Collect siblings until we hit the next heading
                    next_heading = item_headings[i+1]
                    while current and current != next_heading:
                        if current.name and current.get_text().strip():
                            content_elements.append(current)
                        current = current.next_sibling
                
                # Combine the text from all elements
                section_text = ""
                for element in content_elements:
                    if element.name:
                        # Special handling for tables
                        if element.name == 'table':
                            section_text += self._extract_table_text(element) + "\n\n"
                        else:
                            section_text += element.get_text().strip() + "\n\n"
                
                # Create a text chunk for this section
                if section_text.strip():
                    chunk_id = f"{document_id}_text_{i}"
                    text_chunks.append(TextChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        text=section_text.strip(),
                        section=section_title,
                        page_number=None  # SEC HTML files don't have page numbers
                    ))
        
        # Method 2: If method 1 didn't find any sections, look for divs with specific classes
        # SEC often uses div elements with specific classes for sections
        if not text_chunks:
            logger.info("Falling back to div-based section detection")
            
            # Look for common section containers in SEC documents
            section_divs = soup.find_all(['div', 'section'], class_=re.compile(r'(section|part|item)', re.IGNORECASE))
            
            for i, div in enumerate(section_divs):
                # Try to find a heading within this div
                heading = div.find(['h1', 'h2', 'h3', 'h4'])
                section_title = heading.get_text().strip() if heading else f"Section {i+1}"
                
                # Get the text content
                section_text = div.get_text().strip()
                
                # Create a text chunk
                if section_text:
                    chunk_id = f"{document_id}_text_{i}"
                    text_chunks.append(TextChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        text=section_text,
                        section=section_title,
                        page_number=None
                    ))
        
        # Method 3: As a last resort, chunk the document by size if no sections found
        if not text_chunks:
            logger.warning("No sections found, chunking document by size")
            
            # Extract text only from paragraph, div, and section elements
            text_elements = soup.find_all(['p', 'div', 'section'])
            full_text = ""
            for element in text_elements:
                # Only get direct text from these elements, not nested elements
                # This avoids duplicating text from nested elements
                element_text = ''.join(child for child in element.contents 
                                      if isinstance(child, str)).strip()
                if element_text:
                    full_text += element_text + "\n\n"
            
            # Split into chunks of approximately 2000 characters each
            chunk_size = 2000
            chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
            for i, chunk_text in enumerate(chunks):
                if chunk_text.strip():
                    chunk_id = f"{document_id}_text_{i}"
                    text_chunks.append(TextChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        text=chunk_text.strip(),
                        section=f"Chunk {i+1}",
                        page_number=None
                    ))
        logger.info(f"Extracted {len(text_chunks)} text chunks from document")
        return text_chunks
    
    def _extract_table_text(self, table_element) -> str:
        """Extract readable text from an HTML table element."""
        rows = []
        
        # Process each row
        for tr in table_element.find_all('tr'):
            row_cells = []
            
            # Process cells (both th and td)
            for cell in tr.find_all(['th', 'td']):
                # Get just the text, stripping whitespace
                text = cell.get_text().strip()
                # Replace multiple spaces and newlines with a single space
                text = re.sub(r'\s+', ' ', text)
                row_cells.append(text)
            
            if row_cells:  # Skip empty rows
                # Join the cells with pipe separators for readability
                rows.append(' | '.join(row_cells))
        
        # Join rows with newlines
        return '\n'.join(rows)
    
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
            import traceback
            logger.error(f"Error saving document to database: {e} {traceback.format_exc()}")

