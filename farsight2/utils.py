from typing import Optional


def generate_document_id(
    ticker: str, year: int, quarter: Optional[int], filing_type: str
) -> str:
    """
    Generate a standardized document ID from document metadata.

    Args:
        ticker: Company ticker symbol
        year: Filing year
        quarter: Filing quarter (None for 10-K)
        filing_type: Filing type (10-K or 10-Q)

    Returns:
        Formatted document ID string
    """
    return (
        f"{ticker}_{year}_{quarter if quarter else '4'}_{filing_type.replace('-', '')}"
    )
