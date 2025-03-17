"""Document processor for extracting content from 10-K/10-Q filings."""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
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
    
    def process_filing(self, content: str, metadata: DocumentMetadata) -> ParsedDocument:
        """Process a filing and extract its content.
        
        Args:
            content: Content of the filing
            metadata: Metadata for the filing
            
        Returns:
            ParsedDocument containing the extracted content
        """
        logger.info(f"Processing filing: {metadata.document_id}")
        
        # Extract SEC header metadata if available
        sec_metadata = self._extract_sec_metadata(content)
        if sec_metadata:
            # Update metadata with extracted information
            if not metadata.filing_date and 'filing_date' in sec_metadata:
                metadata.filing_date = sec_metadata['filing_date']
                logger.info(f"Updated filing date from SEC header: {metadata.filing_date}")
        
        # Extract filing date if not already set
        if metadata.filing_date is None:
            metadata.filing_date = self._extract_filing_date(content)
            logger.info(f"Extracted filing date: {metadata.filing_date}")
        
        # Extract text chunks
        text_chunks = self._extract_text_chunks(content, metadata.document_id)
        logger.info(f"Extracted {len(text_chunks)} text chunks")
        
        # Extract tables
        tables = self._extract_tables(content, metadata.document_id)
        logger.info(f"Extracted {len(tables)} tables")
        
        # Extract charts
        charts = self._extract_charts(content, metadata.document_id)
        logger.info(f"Extracted {len(charts)} charts")
        
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
    
    def _extract_sec_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from the SEC header section.
        
        SEC filings typically start with a header section containing metadata about the filing.
        This method extracts key information from that section.
        
        Args:
            content: Content of the filing
            
        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}
        
        # Look for the SEC-HEADER section
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', content, re.DOTALL | re.IGNORECASE)
        if not header_match:
            return metadata
        
        header_text = header_match.group(1)
        
        # Extract filing date (FILED AS OF DATE)
        date_match = re.search(r'FILED AS OF DATE:\s*(\d{8})', header_text)
        if date_match:
            date_str = date_match.group(1)
            try:
                metadata['filing_date'] = datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                logger.warning(f"Could not parse filing date: {date_str}")
        
        # Extract company name
        company_match = re.search(r'COMPANY CONFORMED NAME:\s*(.*?)$', header_text, re.MULTILINE)
        if company_match:
            metadata['company_name'] = company_match.group(1).strip()
        
        # Extract CIK
        cik_match = re.search(r'CENTRAL INDEX KEY:\s*(\d+)', header_text)
        if cik_match:
            metadata['cik'] = cik_match.group(1)
        
        # Extract SIC code and industry
        sic_match = re.search(r'STANDARD INDUSTRIAL CLASSIFICATION:\s*(.*?)\[(\d+)\]', header_text)
        if sic_match:
            metadata['industry'] = sic_match.group(1).strip()
            metadata['sic_code'] = sic_match.group(2)
        
        # Extract fiscal year end
        fiscal_year_match = re.search(r'FISCAL YEAR END:\s*(\d{4})', header_text)
        if fiscal_year_match:
            metadata['fiscal_year_end'] = fiscal_year_match.group(1)
        
        return metadata
    
    def _extract_filing_date(self, content: str) -> datetime:
        """Extract the filing date from the document content.
        
        Tries multiple patterns to find the filing date in SEC documents.
        
        Args:
            content: Content of the filing
            
        Returns:
            Filing date as a datetime object
        """
        # Pattern 1: Look for SEC-DOCUMENT line with date
        sec_doc_match = re.search(r'<SEC-DOCUMENT>.*?(\d{8})', content)
        if sec_doc_match:
            date_str = sec_doc_match.group(1)
            try:
                return datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                logger.warning(f"Could not parse SEC-DOCUMENT date: {date_str}")
        
        # Pattern 2: Look for FILED: date
        filed_match = re.search(r'FILED\s*:\s*(\w+)\s+(\d+),\s+(\d{4})', content)
        if filed_match:
            month, day, year = filed_match.groups()
            try:
                return datetime.strptime(f"{month} {day} {year}", "%B %d %Y")
            except ValueError:
                logger.warning(f"Could not parse FILED date: {month} {day}, {year}")
        
        # Pattern 3: Look for CONFORMED PERIOD OF REPORT
        period_match = re.search(r'CONFORMED PERIOD OF REPORT:\s*(\d{8})', content)
        if period_match:
            date_str = period_match.group(1)
            try:
                return datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                logger.warning(f"Could not parse CONFORMED PERIOD date: {date_str}")
        
        # Fallback to current date if extraction fails
        logger.warning("Could not extract filing date, using current date")
        return datetime.now()
    
    def _extract_text_chunks(self, content: str, document_id: str) -> List[TextChunk]:
        """
        Extract text chunks from SEC filing HTML document content.
        
        Optimized for SEC filings which have a specific structure with ITEM sections.
        
        Args:
            content: HTML content of the document
            document_id: ID of the document
            
        Returns:
            List of TextChunk objects
        """
        from bs4 import BeautifulSoup
        import re
        
        # First, check if this is an SEC filing with the characteristic SEC-DOCUMENT tag
        is_sec_filing = bool(re.search(r'<SEC-DOCUMENT>|<SEC-HEADER>', content, re.IGNORECASE))
        
        # For SEC filings, extract the main document content
        if is_sec_filing:
            # Find the main document, usually after the SEC-HEADER
            doc_match = re.search(r'<DOCUMENT>.*?<TYPE>(.*?)</TYPE>.*?<TEXT>(.*?)</TEXT>.*?</DOCUMENT>', 
                                  content, re.DOTALL | re.IGNORECASE)
            if doc_match:
                doc_type, doc_content = doc_match.groups()
                # If it's the main filing (10-K or 10-Q), use that content
                if re.match(r'10-[KQ](/A)?', doc_type, re.IGNORECASE):
                    logger.info(f"Found main document of type {doc_type}")
                    content = doc_content
        
        # Parse HTML content
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove script and style elements that aren't relevant
        for element in soup(["script", "style", "head", "meta", "link"]):
            element.extract()
        
        # Look for common 10-K/10-Q section patterns
        text_chunks = []
        
        # Method 1: Look specifically for SEC ITEM sections
        # SEC filings follow a standard structure with numbered ITEM sections
        item_pattern = r'^ITEM\s+\d+[A-Z]?\.?\s*[-—–]?\s*([A-Z0-9\s,\.]+)'
        
        # Find potential ITEM headings using broader selectors
        potential_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'div', 'p', 'span', 'b', 'strong', 'font'], 
                                          string=re.compile(r'^\s*ITEM\s+\d+', re.IGNORECASE))
        
        # Filter out false positives by checking context
        item_headings = []
        for heading in potential_headings:
            # Get the text and strip whitespace
            text = heading.get_text().strip()
            
            # Check if it matches our pattern for SEC ITEM headings
            if re.match(item_pattern, text, re.IGNORECASE):
                # Check if this is reasonably sized (not a full paragraph mentioning an item)
                if len(text) < 200:  # Heading should be short
                    item_headings.append(heading)
        
        # If we found item headings, extract content between them
        if item_headings:
            logger.info(f"Found {len(item_headings)} SEC ITEM headings")
            
            # Sort headings by their position in the document
            # This is important because BS4 find_all doesn't guarantee order
            item_headings.sort(key=lambda x: content.find(str(x)))
            
            # Identify parent elements that might contain both the heading and content
            sections = []
            for i, heading in enumerate(item_headings):
                section_title = heading.get_text().strip()
                
                # Check if heading has a parent div or section that contains the content
                parent = heading.find_parent(['div', 'section'])
                if parent:
                    # Check if this parent contains multiple headings (if so, it's too broad)
                    other_items = parent.find_all(string=re.compile(r'^\s*ITEM\s+\d+', re.IGNORECASE))
                    if len(other_items) == 1:
                        # Just contains this item, so use the parent
                        sections.append((section_title, parent))
                        continue
                
                # Otherwise extract content between this heading and the next one
                # Collect all elements until the next heading or end of document
                next_heading = item_headings[i+1] if i < len(item_headings) - 1 else None
                
                # Start with the heading itself
                content_elements = [heading]
                current = heading.next_sibling
                
                while current and (not next_heading or current != next_heading):
                    if current.name:  # Only include actual elements
                        content_elements.append(current)
                    # Move to next sibling
                    current = current.next_sibling
                
                sections.append((section_title, content_elements))
            
            # Process each section and create text chunks
            for i, (section_title, section_content) in enumerate(sections):
                # Extract text depending on whether section_content is a list or a single element
                if isinstance(section_content, list):
                    section_text = ""
                    for element in section_content:
                        if element.name:
                            # Special handling for tables
                            if element.name == 'table':
                                section_text += self._extract_table_text(element) + "\n\n"
                            else:
                                section_text += element.get_text().strip() + "\n\n"
                else:
                    # It's a single element like a div
                    section_text = section_content.get_text().strip()
                
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
        
        # Method 2: If Method 1 didn't work, look for divs with specific SEC classes or IDs
        if not text_chunks:
            logger.info("Falling back to div-based section detection")
            
            # SEC filings often use specific class names or IDs for sections
            section_selectors = [
                # Modern SEC filings use these classes
                {'class': re.compile(r'(item|part)-\d+', re.IGNORECASE)},
                {'id': re.compile(r'(item|part)-\d+', re.IGNORECASE)},
                # Older filings might use these
                {'class': re.compile(r'(section|part|item)', re.IGNORECASE)},
                {'id': re.compile(r'(section|part|item)', re.IGNORECASE)}
            ]
            
            # Try each selector
            for selector in section_selectors:
                section_elements = soup.find_all(['div', 'section'], **selector)
                if section_elements:
                    logger.info(f"Found {len(section_elements)} sections using selector {selector}")
                    break
            else:
                # If none worked, try a more general approach
                section_elements = []
            
            # Process each section
            for i, div in enumerate(section_elements):
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
        
        # Method 3: As a last resort, use a content-based approach to identify sections
        if not text_chunks:
            logger.warning("No sections found, using content-based section detection")
            
            # Get the full text content
            full_text = soup.get_text()
            
            # Use regex to find ITEM sections directly in the text
            item_matches = list(re.finditer(r'(ITEM\s+\d+[A-Z]?\.?\s*[-—–]?\s*[A-Z0-9\s,\.]+)', full_text, re.IGNORECASE))
            
            if item_matches:
                logger.info(f"Found {len(item_matches)} ITEM sections in text")
                
                # Extract content between matched headings
                for i, match in enumerate(item_matches):
                    section_title = match.group(1).strip()
                    start_pos = match.end()
                    
                    # Find the end position (start of next section or end of text)
                    if i < len(item_matches) - 1:
                        end_pos = item_matches[i+1].start()
                    else:
                        end_pos = len(full_text)
                    
                    # Extract the section text
                    section_text = full_text[start_pos:end_pos].strip()
                    
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
            else:
                logger.warning("No ITEM sections found in text, chunking by size")
                
                # Split into chunks of approximately 3000 characters each
                chunk_size = 3000
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
        """Extract readable text from an HTML table element, optimized for SEC filings.
        
        SEC tables often have specific formats that need special handling.
        
        Args:
            table_element: BeautifulSoup table element
            
        Returns:
            String representation of the table
        """
        rows = []
        
        # Check if the table has a title/caption
        caption = table_element.find('caption')
        if caption:
            rows.append(f"TABLE: {caption.get_text().strip()}")
            rows.append("")  # Empty line after caption
        
        # Check if the table has headers in a thead
        thead = table_element.find('thead')
        if thead:
            header_cells = []
            for th in thead.find_all(['th', 'td']):
                header_cells.append(th.get_text().strip())
            if header_cells:
                rows.append(' | '.join(header_cells))
                rows.append('-' * (sum(len(cell) for cell in header_cells) + 3 * len(header_cells)))  # Separator line
        
        # Process the table body
        tbody = table_element.find('tbody') or table_element  # Use tbody if it exists, otherwise the whole table
        
        # Process each row
        for tr in tbody.find_all('tr'):
            row_cells = []
            
            # Process cells (both th and td)
            for cell in tr.find_all(['th', 'td']):
                # Get just the text, stripping whitespace
                text = cell.get_text().strip()
                # Replace multiple spaces and newlines with a single space
                text = re.sub(r'\s+', ' ', text)
                
                # Handle colspan attribute if present
                colspan = cell.get('colspan')
                if colspan and colspan.isdigit() and int(colspan) > 1:
                    # Repeat the cell content for colspan
                    row_cells.extend([text] * int(colspan))
                else:
                    row_cells.append(text)
            
            if row_cells:  # Skip empty rows
                # Join the cells with pipe separators for readability
                rows.append(' | '.join(row_cells))
        
        # Join rows with newlines
        return '\n'.join(rows)
    
    def _extract_tables(self, content: str, document_id: str) -> List[Table]:
        """Extract tables from the SEC filing content.
        
        Args:
            content: Content of the filing
            document_id: ID of the document
            
        Returns:
            List of Table objects
        """
        from bs4 import BeautifulSoup
        
        # Parse HTML content
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all tables in the document
        tables = []
        
        # First, look for tables with specific classes often used in SEC filings
        sec_tables = soup.find_all('table', class_=re.compile(r'(financial|report|data)', re.IGNORECASE))
        
        # If no tables with specific classes found, get all tables
        all_tables = sec_tables if sec_tables else soup.find_all('table')
        
        # Process each table
        for i, table_element in enumerate(all_tables):
            # Skip small tables (likely layout tables, not data tables)
            rows = table_element.find_all('tr')
            if len(rows) < 2:  # Need at least 2 rows for a meaningful table
                continue
                
            chunk_id = f"{document_id}_table_{i}"
            
            # Try to find a caption
            caption_element = table_element.find('caption')
            caption = caption_element.get_text().strip() if caption_element else None
            
            # If no caption, look for text right before the table that might be a caption
            if not caption:
                prev_el = table_element.find_previous(['p', 'div', 'h3', 'h4'])
                if prev_el and len(prev_el.get_text().strip()) < 200:  # Reasonable caption length
                    caption = prev_el.get_text().strip()
            
            # Find the section this table belongs to
            section = "Unknown"
            
            # Look for the nearest heading that might be a section title
            current = table_element
            while current:
                if current.name in ['h1', 'h2', 'h3', 'h4']:
                    section_text = current.get_text().strip()
                    # Check if it looks like an ITEM section heading
                    if re.match(r'^\s*ITEM\s+\d+', section_text, re.IGNORECASE):
                        section = section_text
                        break
                current = current.find_previous()
            
            # If we didn't find a section heading, try to find the closest div with an id or class
            if section == "Unknown":
                parent_div = table_element.find_parent(['div', 'section'])
                if parent_div:
                    if parent_div.get('id'):
                        section = f"Section: {parent_div.get('id')}"
                    elif parent_div.get('class'):
                        section = f"Section: {' '.join(parent_div.get('class'))}"
            
            # Extract structured data from the table
            table_data = []
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if cells:
                    row_data = [cell.get_text().strip() for cell in cells]
                    table_data.append(row_data)
            
            # Create Table object
            tables.append(Table(
                chunk_id=chunk_id,
                document_id=document_id,
                table_html=str(table_element),
                table_data=table_data if table_data else None,
                caption=caption,
                section=section,
                page_number=None
            ))
        
        return tables
    
    def _extract_charts(self, content: str, document_id: str) -> List[Chart]:
        """Extract charts and figures from the SEC filing content.
        
        Args:
            content: Content of the filing
            document_id: ID of the document
            
        Returns:
            List of Chart objects
        """
        from bs4 import BeautifulSoup
        
        # Parse HTML content
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all images that might be charts
        charts = []
        image_elements = soup.find_all('img')
        
        for i, img in enumerate(image_elements):
            # Skip small images (likely icons or logos)
            width = img.get('width')
            height = img.get('height')
            if width and height:
                try:
                    if int(width) < 100 or int(height) < 100:
                        continue
                except ValueError:
                    pass  # Width/height not integer values
            
            chunk_id = f"{document_id}_chart_{i}"
            
            # Try to find a caption
            caption = None
            
            # Look for a figcaption element
            figcaption = img.find_parent('figure')
            if figcaption:
                caption_el = figcaption.find('figcaption')
                if caption_el:
                    caption = caption_el.get_text().strip()
            
            # If no figcaption, look at the alt text or title
            if not caption:
                caption = img.get('alt') or img.get('title')
            
            # If still no caption, look for text right after the image
            if not caption:
                next_el = img.find_next(['p', 'div', 'span'])
                if next_el and len(next_el.get_text().strip()) < 200:  # Reasonable caption length
                    caption = next_el.get_text().strip()
            
            # Find the section this chart belongs to
            section = "Unknown"
            
            # Look for the nearest heading that might be a section title
            current = img
            while current:
                if current.name in ['h1', 'h2', 'h3', 'h4']:
                    section_text = current.get_text().strip()
                    # Check if it looks like an ITEM section heading
                    if re.match(r'^\s*ITEM\s+\d+', section_text, re.IGNORECASE):
                        section = section_text
                        break
                current = current.find_previous()
            
            # Create chart data
            chart_data = {
                'src': img.get('src'),
                'alt': img.get('alt'),
                'width': width,
                'height': height
            }
            
            # Create Chart object
            charts.append(Chart(
                chunk_id=chunk_id,
                document_id=document_id,
                chart_data=chart_data,
                caption=caption,
                section=section,
                page_number=None
            ))
        
        return charts

    def _save_to_database(self, parsed_document: ParsedDocument) -> None:
        """Save the parsed document to the database.
        
        Args:
            parsed_document: Parsed document to save
        """
        try:
            # Save via the repository
            self.repository.create_document(parsed_document.metadata)
            
            # Save text chunks
            for text_chunk in parsed_document.text_chunks:
                self.repository.create_text_chunk(text_chunk)
            
            # Save tables
            for table in parsed_document.tables:
                self.repository.create_table(table)
            
            # Save charts
            for chart in parsed_document.charts:
                self.repository.create_chart(chart)
            
            logger.info(f"Saved document {parsed_document.document_id} to database")
        except Exception as e:
            import traceback
            logger.error(f"Error saving document to database: {e} {traceback.format_exc()}")
    
    def process_document(self, file_path: str, ticker: str, year: int, quarter: Optional[int], filing_type: str) -> ParsedDocument:
        """Process a document from a file.
        
        Args:
            file_path: Path to the document file
            ticker: Company ticker symbol
            year: Filing year
            quarter: Filing quarter (None for 10-K)
            filing_type: Filing type (10-K or 10-Q)
            
        Returns:
            ParsedDocument containing the extracted content
        """
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Create document metadata
            document_id = f"{ticker}_{year}_{quarter if quarter else 'annual'}_{filing_type.replace('-', '')}"
            
            # Check if company exists, create if not
            company = self.repository.get_company(ticker)
            if not company:
                company = self.repository.create_company(ticker, ticker)  # Use ticker as name initially
            
            # Create document metadata
            metadata = DocumentMetadata(
                document_id=document_id,
                ticker=ticker,
                year=year,
                quarter=quarter,
                filing_type=filing_type
            )
            
            # Process the filing
            return self.process_filing(content, metadata)
            
        except Exception as e:
            import traceback
            logger.error(f"Error processing document: {e} {traceback.format_exc()}")
            raise
    
    def _parse_document(self, content: str, document_id: str) -> ParsedDocument:
        """Parse a document directly from content string.
        
        This is a helper method for testing and direct parsing without file I/O.
        
        Args:
            content: Content of the document
            document_id: ID to assign to the document
            
        Returns:
            ParsedDocument containing the extracted content
        """
        # Extract ticker, year, quarter, filing_type from document_id
        parts = document_id.split('_')
        if len(parts) >= 4:
            ticker = parts[0]
            year = int(parts[1])
            quarter = int(parts[2]) if parts[2].isdigit() else None
            filing_type = parts[3]
            
            # Create metadata
            metadata = DocumentMetadata(
                document_id=document_id,
                ticker=ticker,
                year=year,
                quarter=quarter,
                filing_type=filing_type
            )
            
            # Process the filing
            return self.process_filing(content, metadata)
        else:
            raise ValueError(f"Invalid document_id format: {document_id}")

