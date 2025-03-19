"""Document selector for determining which documents are needed for a query."""

import logging
from typing import List, Dict
from datetime import datetime


from farsight2.models.models import QueryAnalysis, DocumentReference, DocumentMetadata

logger = logging.getLogger(__name__)


class DocumentSelector:
    """Selector for determining which documents are needed for a query."""

    def __init__(self, document_registry: Dict[str, List[DocumentMetadata]]):
        """Initialize the document selector.

        Args:
            document_registry: Dictionary mapping company tickers to lists of document metadata
        """
        self.document_registry = document_registry
        from farsight2.database.unified_repository import UnifiedRepository

        self.repository = UnifiedRepository()

    def select_documents(
        self, query_analysis: QueryAnalysis
    ) -> List[DocumentReference]:
        """Select documents that are relevant to a query.

        Args:
            query_analysis: Analysis of the query

        Returns:
            List of document references
        """
        logger.info(
            f"Selecting documents for query: {query_analysis.model_dump(exclude={'embedding'})}"
        )

        document_references = []

        # Get companies from the query analysis
        companies = query_analysis.companies

        # If no companies specified, return empty list
        if not companies:
            logger.warning("No companies specified in the query")
            return []

        # Get years and quarters from the query analysis
        years = query_analysis.years
        quarters = query_analysis.quarters

        # If no years specified, use the most recent year
        if not years:
            current_year = datetime.now().year
            years = [current_year]

        # For each company, find the relevant documents
        for company in companies:
            # Check if we have documents for this company
            if company not in self.document_registry:
                logger.warning(f"No documents found for company: {company}")
                continue

            # Get all documents for this company
            company_documents = self.repository.get_documents_by_company(company)

            print(f"Company documents: {company_documents}")

            # Filter by year and quarter
            for year in years:
                # Find 10-K for this year
                annual_docs = [
                    doc
                    for doc in company_documents
                    if doc.year == year and doc.filing_type == "10-K"
                ]

                # Add annual report with high relevance
                for doc in annual_docs:
                    document_references.append(
                        DocumentReference(
                            document_id=doc.document_id,
                            relevance_score=1.0,  # Highest relevance
                        )
                    )

                # If quarters specified, find 10-Q for those quarters
                if not quarters:
                    quarters = [1, 2, 3, 4]
                if quarters:
                    for quarter in quarters:
                        # Skip Q4 as it's covered by 10-K
                        if quarter == 4:
                            continue

                        quarterly_docs = [
                            doc
                            for doc in company_documents
                            if doc.year == year
                            and doc.filing_type == "10-Q"
                            and doc.quarter == quarter
                        ]

                        # Add quarterly reports with high relevance
                        for doc in quarterly_docs:
                            document_references.append(
                                DocumentReference(
                                    document_id=doc.document_id,
                                    relevance_score=0.9,  # High relevance
                                )
                            )
                else:
                    # If no quarters specified, include all quarterly reports for the year
                    quarterly_docs = [
                        doc
                        for doc in company_documents
                        if doc.year == year and doc.filing_type == "10-Q"
                    ]

                    # Add quarterly reports with medium relevance
                    for doc in quarterly_docs:
                        document_references.append(
                            DocumentReference(
                                document_id=doc.document_id,
                                relevance_score=0.8,  # Medium relevance
                            )
                        )

        # Sort by relevance score
        document_references.sort(key=lambda x: x.relevance_score, reverse=True)

        return document_references
