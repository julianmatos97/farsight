"""Document processor for extracting content from 10-K/10-Q filings."""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from farsight2.models.models import (
    DocumentMetadata,
    ParsedDocument,
    TextChunk,
    Table,
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
        self.embedding_service = embedding_service or UnifiedEmbeddingService(
            repository=self.repository
        )

        # Common patterns for SEC filings
        self.section_patterns = [
            r"ITEM\s+\d+[A-Z]?\.?\s*[-—–]?\s*([A-Z0-9\s,\.]+)",  # Standard ITEM pattern
            r"PART\s+[IVX]+\.?\s*[-—–]?\s*([A-Z0-9\s,\.]+)",  # PART pattern
            r"Notes?\s+to\s+[Cc]onsolidated\s+[Ff]inancial\s+[Ss]tatements?",  # Notes pattern
            r"Management\'s\s+Discussion\s+and\s+Analysis",  # MD&A pattern
            r"Risk\s+Factors?",  # Risk Factors pattern
            r"Business",  # Business section pattern
            r"Financial\s+Statements?\s+and\s+Supplementary\s+Data",  # Financial statements pattern
        ]

    def process_filing(
        self, content: str, metadata: DocumentMetadata
    ) -> ParsedDocument:
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
            if not metadata.filing_date and "filing_date" in sec_metadata:
                metadata.filing_date = sec_metadata["filing_date"]
                logger.info(
                    f"Updated filing date from SEC header: {metadata.filing_date}"
                )

        # Extract filing date if not already set
        if metadata.filing_date is None:
            metadata.filing_date = self._extract_filing_date(content)
            logger.info(f"Extracted filing date: {metadata.filing_date}")

        # Extract text chunks
        text_chunks = self._extract_text_chunks(content, metadata.document_id)
        logger.info(f"Extracted {len(text_chunks)} text chunks")

        # Extract tables
        # tables = self._extract_tables(content, metadata.document_id)
        # logger.info(f"Extracted {len(tables)} tables")

        # # Extract charts
        # charts = self._extract_charts(content, metadata.document_id)
        # logger.info(f"Extracted {len(charts)} charts")

        # Create parsed document
        parsed_document = ParsedDocument(
            document_id=metadata.document_id,
            metadata=metadata,
            text_chunks=text_chunks,
            tables=[],
            charts=[],
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
        header_match = re.search(
            r"<SEC-HEADER>(.*?)</SEC-HEADER>", content, re.DOTALL | re.IGNORECASE
        )
        if not header_match:
            return metadata

        header_text = header_match.group(1)

        # Extract filing date (FILED AS OF DATE)
        date_match = re.search(r"FILED AS OF DATE:\s*(\d{8})", header_text)
        if date_match:
            date_str = date_match.group(1)
            try:
                metadata["filing_date"] = datetime.strptime(date_str, "%Y%m%d")
            except ValueError:
                logger.warning(f"Could not parse filing date: {date_str}")

        # Extract company name
        company_match = re.search(
            r"COMPANY CONFORMED NAME:\s*(.*?)$", header_text, re.MULTILINE
        )
        if company_match:
            metadata["company_name"] = company_match.group(1).strip()

        # Extract CIK
        cik_match = re.search(r"CENTRAL INDEX KEY:\s*(\d+)", header_text)
        if cik_match:
            metadata["cik"] = cik_match.group(1)

        # Extract SIC code and industry
        sic_match = re.search(
            r"STANDARD INDUSTRIAL CLASSIFICATION:\s*(.*?)\[(\d+)\]", header_text
        )
        if sic_match:
            metadata["industry"] = sic_match.group(1).strip()
            metadata["sic_code"] = sic_match.group(2)

        # Extract fiscal year end
        fiscal_year_match = re.search(r"FISCAL YEAR END:\s*(\d{4})", header_text)
        if fiscal_year_match:
            metadata["fiscal_year_end"] = fiscal_year_match.group(1)

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
        sec_doc_match = re.search(r"<SEC-DOCUMENT>.*?(\d{8})", content)
        if sec_doc_match:
            date_str = sec_doc_match.group(1)
            try:
                return datetime.strptime(date_str, "%Y%m%d")
            except ValueError:
                logger.warning(f"Could not parse SEC-DOCUMENT date: {date_str}")

        # Pattern 2: Look for FILED: date
        filed_match = re.search(r"FILED\s*:\s*(\w+)\s+(\d+),\s+(\d{4})", content)
        if filed_match:
            month, day, year = filed_match.groups()
            try:
                return datetime.strptime(f"{month} {day} {year}", "%B %d %Y")
            except ValueError:
                logger.warning(f"Could not parse FILED date: {month} {day}, {year}")

        # Pattern 3: Look for CONFORMED PERIOD OF REPORT
        period_match = re.search(r"CONFORMED PERIOD OF REPORT:\s*(\d{8})", content)
        if period_match:
            date_str = period_match.group(1)
            try:
                return datetime.strptime(date_str, "%Y%m%d")
            except ValueError:
                logger.warning(f"Could not parse CONFORMED PERIOD date: {date_str}")

        # Fallback to current date if extraction fails
        logger.warning("Could not extract filing date, using current date")
        return datetime.now()

    def _extract_text_chunks(self, content: str, document_id: str) -> List[TextChunk]:
        """Extract pure text content from SEC filing, excluding tables and charts.

        This method focuses on extracting meaningful text sections while preserving document structure.
        It specifically excludes tables and chart content which are handled separately.

        Args:
            content: HTML content of the filing
            document_id: ID of the document

        Returns:
            List of TextChunk objects containing pure text content
        """
        from bs4 import BeautifulSoup
        import re

        # Parse HTML content
        soup = BeautifulSoup(content, "html.parser")

        # Remove script, style, and other non-content elements
        for element in soup(["script", "style", "meta", "link", "img"]):
            element.decompose()

        # Remove all table elements (they'll be processed separately)
        for table in soup.find_all("table"):
            table.decompose()

        # Initialize chunks list
        text_chunks = []
        chunk_id_counter = 0

        def create_chunk(text: str, section: str) -> Optional[TextChunk]:
            """Helper to create a text chunk if content is meaningful."""
            nonlocal chunk_id_counter

            # Clean the text
            text = re.sub(r"\s+", " ", text).strip()

            # Skip empty or very short chunks
            if not text or len(text) < 50:  # Minimum meaningful chunk size
                return None

            chunk_id = f"{document_id}_text_{chunk_id_counter}"
            chunk_id_counter += 1

            return TextChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                text=text,
                section=section,
                page_number=None,  # HTML doesn't have page numbers
            )

        # First pass: Find major sections
        current_section = "Header"
        current_text = []

        for element in soup.find_all(["div", "p", "h1", "h2", "h3", "h4", "h5", "h6"]):
            text = element.get_text().strip()

            # Check if this element starts a new section
            is_new_section = False
            for pattern in self.section_patterns:
                if re.match(pattern, text, re.IGNORECASE):
                    # If we have accumulated text, create a chunk for the previous section
                    if current_text:
                        chunk = create_chunk(" ".join(current_text), current_section)
                        if chunk:
                            text_chunks.append(chunk)

                    # Start new section
                    current_section = text
                    current_text = []
                    is_new_section = True
                    break

            if not is_new_section:
                # Skip elements that look like table headers or footers
                if re.search(
                    r"table of contents|index to financial statements",
                    text,
                    re.IGNORECASE,
                ):
                    continue

                # Skip elements that are likely navigation or UI elements
                if len(text) < 20 and re.search(
                    r"next|previous|page|top", text, re.IGNORECASE
                ):
                    continue

                # Add text to current section
                if text:
                    current_text.append(text)

            # Create chunks if text buffer gets too large
            if len(" ".join(current_text)) > 1500:  # Maximum chunk size
                chunk = create_chunk(" ".join(current_text), current_section)
                if chunk:
                    text_chunks.append(chunk)
                current_text = []

        # Don't forget the last chunk
        if current_text:
            chunk = create_chunk(" ".join(current_text), current_section)
            if chunk:
                text_chunks.append(chunk)

        # Post-process chunks
        final_chunks = []
        for chunk in text_chunks:
            # Clean up common SEC filing artifacts
            text = chunk.text
            text = re.sub(r"\[\s*\d+\s*\]", "", text)  # Remove reference numbers
            text = re.sub(
                r"\s*\([Cc]ontinued\)\s*", "", text
            )  # Remove (continued) markers
            text = re.sub(
                r"\s*\(table\s+of\s+contents\)\s*", "", text, flags=re.IGNORECASE
            )

            # Update chunk with cleaned text
            if len(text.strip()) >= 50:  # Only keep meaningful chunks
                chunk.text = text.strip()
                final_chunks.append(chunk)

        logger.info(
            f"Extracted {len(final_chunks)} text chunks from document {document_id}"
        )
        return final_chunks

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
        caption = table_element.find("caption")
        if caption:
            rows.append(f"TABLE: {caption.get_text().strip()}")
            rows.append("")  # Empty line after caption

        # Check if the table has headers in a thead
        thead = table_element.find("thead")
        if thead:
            header_cells = []
            for th in thead.find_all(["th", "td"]):
                header_cells.append(th.get_text().strip())
            if header_cells:
                rows.append(" | ".join(header_cells))
                rows.append(
                    "-"
                    * (sum(len(cell) for cell in header_cells) + 3 * len(header_cells))
                )  # Separator line

        # Process the table body
        tbody = (
            table_element.find("tbody") or table_element
        )  # Use tbody if it exists, otherwise the whole table

        # Process each row
        for tr in tbody.find_all("tr"):
            row_cells = []

            # Process cells (both th and td)
            for cell in tr.find_all(["th", "td"]):
                # Get just the text, stripping whitespace
                text = cell.get_text().strip()
                # Replace multiple spaces and newlines with a single space
                text = re.sub(r"\s+", " ", text)

                # Handle colspan attribute if present
                colspan = cell.get("colspan")
                if colspan and colspan.isdigit() and int(colspan) > 1:
                    # Repeat the cell content for colspan
                    row_cells.extend([text] * int(colspan))
                else:
                    row_cells.append(text)

            if row_cells:  # Skip empty rows
                # Join the cells with pipe separators for readability
                rows.append(" | ".join(row_cells))

        # Join rows with newlines
        return "\n".join(rows)

    def _extract_tables(self, content: str, document_id: str) -> List[Table]:
        """Extract complete tables from the SEC filing content.

        This method focuses on extracting structured table data while preserving formatting
        and relationships between cells. It handles complex SEC filing tables including
        nested tables, merged cells, and footnotes.

        Args:
            content: HTML content of the filing
            document_id: ID of the document

        Returns:
            List of Table objects containing structured table data
        """
        from bs4 import BeautifulSoup

        # Parse HTML content
        soup = BeautifulSoup(content, "html.parser")
        tables = []
        table_id_counter = 0

        def get_cell_text(cell) -> str:
            """Extract clean text from a table cell."""
            # Remove nested tables to prevent duplicate content
            for nested_table in cell.find_all("table"):
                nested_table.decompose()

            text = cell.get_text().strip()
            # Clean up common artifacts
            text = re.sub(r"\s+", " ", text)  # Normalize whitespace
            text = re.sub(r"\[\s*\d+\s*\]", "", text)  # Remove reference numbers
            text = re.sub(
                r"\s*\([Cc]ontinued\)\s*", "", text
            )  # Remove (continued) markers
            return text

        def get_table_title(table_element) -> Optional[str]:
            """Extract table title from caption or surrounding context."""
            # Check for caption tag
            caption = table_element.find("caption")
            if caption:
                return caption.get_text().strip()

            # Look for title in parent elements
            parent = table_element.parent
            while parent and parent.name not in ["body", "html"]:
                # Check for common title patterns
                for sibling in parent.find_all_previous(limit=2):
                    if sibling.name in ["p", "div", "h3", "h4", "h5", "h6"]:
                        text = sibling.get_text().strip()
                        # Look for patterns that indicate a table title
                        if re.search(
                            r"table\s+\d+|schedule\s+\d+", text, re.IGNORECASE
                        ):
                            return text
                parent = parent.parent

            return None

        def get_table_section(table_element) -> str:
            """Determine which section the table belongs to."""
            current = table_element
            while current:
                if current.name in ["h1", "h2", "h3", "h4"]:
                    text = current.get_text().strip()
                    # Check if it matches any of our section patterns
                    for pattern in self.section_patterns:
                        if re.match(pattern, text, re.IGNORECASE):
                            return text
                current = current.find_previous()
            return "Unknown Section"

        def process_table(table_element) -> Optional[Table]:
            """Process a single table element and create a Table object."""
            nonlocal table_id_counter

            # Skip small tables that are likely formatting artifacts
            rows = table_element.find_all("tr")
            if len(rows) < 2:  # Need at least header and one data row
                return None

            # Get table metadata
            title = get_table_title(table_element)
            section = get_table_section(table_element)

            # Extract header rows
            header_rows = []
            current_row = rows[0]
            while current_row and (
                current_row.find("th")
                or re.search(
                    r"(in\s+millions|in\s+thousands|year\s+ended|three\s+months\s+ended)",
                    current_row.get_text(),
                    re.IGNORECASE,
                )
            ):
                header_rows.append(current_row)
                if len(rows) > len(header_rows):
                    current_row = rows[len(header_rows)]
                else:
                    break

            # Process table data
            table_data = []

            # Process headers first
            headers = []
            for header_row in header_rows:
                header_cells = []
                for cell in header_row.find_all(["th", "td"]):
                    colspan = int(cell.get("colspan", 1))
                    text = get_cell_text(cell)
                    header_cells.extend([text] * colspan)
                headers.append(header_cells)

            # Process data rows
            for row in rows[len(header_rows) :]:
                row_data = []
                for cell in row.find_all(["td", "th"]):
                    colspan = int(cell.get("colspan", 1))
                    rowspan = int(cell.get("rowspan", 1))
                    text = get_cell_text(cell)

                    # Handle merged cells
                    row_data.extend([text] * colspan)

                    # Handle rowspan by adding the cell value to subsequent rows
                    if rowspan > 1:
                        for i in range(1, rowspan):
                            if len(table_data) + i < len(rows) - len(header_rows):
                                while len(table_data) + i >= len(table_data):
                                    table_data.append([])
                                table_data[len(table_data) + i - 1].extend(
                                    [text] * colspan
                                )

                if row_data:  # Skip empty rows
                    table_data.append(row_data)

            # Skip tables that are likely navigation or formatting elements
            if not table_data or all(
                not any(cell for cell in row) for row in table_data
            ):
                return None

            # Create structured table data including headers
            structured_data = headers + table_data

            # Create Table object
            chunk_id = f"{document_id}_table_{table_id_counter}"
            table_id_counter += 1

            return Table(
                chunk_id=chunk_id,
                document_id=document_id,
                table_html=str(table_element),
                table_data=structured_data,
                caption=title,
                section=section,
                page_number=None,
            )

        # Find all tables in the document
        table_elements = soup.find_all("table")

        # Process each table
        for table_element in table_elements:
            # Skip nested tables (they'll be handled as part of their parent)
            if not any(parent.name == "table" for parent in table_element.parents):
                table = process_table(table_element)
                if table:
                    tables.append(table)

        logger.info(f"Extracted {len(tables)} tables from document {document_id}")
        return tables

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

            logger.info(f"Saved document {parsed_document.document_id} to database")
        except Exception as e:
            import traceback

            logger.error(
                f"Error saving document to database: {e} {traceback.format_exc()}"
            )

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
        parts = document_id.split("_")
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
                filing_type=filing_type,
            )

            # Process the filing
            return self.process_filing(content, metadata)
        else:
            raise ValueError(f"Invalid document_id format: {document_id}")
