"""Client for downloading 10-K/10-Q filings from the SEC EDGAR database."""

import logging
import requests
import time
from typing import Optional, Dict, Any, List, Tuple
import os
import json
from datetime import datetime

from farsight2.utils import generate_document_id
from farsight2.database.unified_repository import UnifiedRepository
from farsight2.models.models import DocumentMetadata, Fact, FactValue
from farsight2.embedding.unified_embedding_service import UnifiedEmbeddingService

logger = logging.getLogger(__name__)


class EdgarClient:
    """Client for downloading 10-K/10-Q filings from the SEC EDGAR database."""

    ARCHIVE_URL = "https://www.sec.gov/Archives"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions"
    TICKER_LOOKUP_URL = "https://www.sec.gov/files/company_tickers.json"
    XBRL_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    XBRL_COMPANYCONCEPT_URL = (
        "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json"
    )
    USER_AGENT = (
        "Farsight2/0.1.0 (contact@example.com)"  # Replace with your contact info
    )
    SUPPORTED_TAXONOMIES = ["us-gaap", "dei", "srt", "ifrs-full"]
    SUPPORTED_UNITS = ["USD", "shares", "pure", "usd-per-shares", "number"]

    def __init__(self, download_dir: Optional[str] = None):
        """Initialize the EDGAR client.

        Args:
            download_dir: Directory to save downloaded files. Defaults to data/downloads.
        """
        self.download_dir = download_dir or os.path.join(
            os.path.dirname(__file__), "../../data/downloads"
        )
        os.makedirs(self.download_dir, exist_ok=True)
        self.repository = UnifiedRepository()
        self.embedding_service = UnifiedEmbeddingService()

        # Cache for CIK lookups to minimize API calls
        self.cik_cache = {}
        self._load_cik_cache()

    def _load_cik_cache(self):
        """Load CIK cache from file if it exists."""
        cache_file = os.path.join(self.download_dir, "cik_cache.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    self.cik_cache = json.load(f)
                logger.info(f"Loaded {len(self.cik_cache)} CIKs from cache")
            except Exception as e:
                logger.warning(f"Failed to load CIK cache: {e}")

    def _save_cik_cache(self):
        """Save CIK cache to file."""
        cache_file = os.path.join(self.download_dir, "cik_cache.json")
        try:
            with open(cache_file, "w") as f:
                json.dump(self.cik_cache, f)
            logger.info(f"Saved {len(self.cik_cache)} CIKs to cache")
        except Exception as e:
            logger.warning(f"Failed to save CIK cache: {e}")

    def get_company_filings(self, ticker: str) -> Dict[str, Any]:
        """Get all filings for a company using the submissions API.

        Args:
            ticker: Company ticker symbol

        Returns:
            Dictionary containing company filing information
        """
        cik = self._format_cik(ticker)
        url = f"{self.SUBMISSIONS_URL}/CIK{cik}.json"
        logger.info(f"Fetching company filings from: {url}")

        response = self._make_request(url)
        data = response.json()

        # Log a simpler message and dump the full data to a file for inspection
        logger.info(f"Fetched company filings for {ticker}")

        # Cache the CIK if we found it
        if data and ticker.upper() not in self.cik_cache:
            self.cik_cache[ticker.upper()] = cik
            self._save_cik_cache()

        return data

    def find_filing_url(
        self, ticker: str, year: int, quarter: Optional[int], filing_type: str
    ) -> Dict[str, Any]:
        """Find the URL for a specific filing using the submissions API.

        Args:
            ticker: Company ticker symbol
            year: Filing year
            quarter: Filing quarter (None for 10-K)
            filing_type: Filing type (10-K or 10-Q)

        Returns:
            URL of the filing

        Raises:
            Exception: If the filing cannot be found
        """
        # Get all filings using the submissions API
        filings_data = self.get_company_filings(ticker)

        # Extract the recent filings from the data
        recent_filings = filings_data.get("filings", {}).get("recent", {})
        if not recent_filings:
            raise Exception(f"No recent filings found for {ticker}")

        # The filings data is in a columnar format where each property is an array
        form_array = recent_filings.get("form", [])
        filing_date_array = recent_filings.get("filingDate", [])
        accession_number_array = recent_filings.get("accessionNumber", [])
        # primary_document_array = recent_filings.get("primaryDocument", [])
        if not form_array or not filing_date_array or not accession_number_array:
            raise Exception(f"Missing filing data for {ticker}")

        # Find matching filings
        matches = []
        for i in range(len(form_array)):
            form = form_array[i]
            filing_date = filing_date_array[i]
            accession_number = accession_number_array[i]
            # Parse the filing date to get the year and quarter
            try:
                date_obj = datetime.strptime(filing_date, "%Y-%m-%d")
                filing_year = date_obj.year
                filing_quarter = (date_obj.month - 1) // 3 + 1
            except Exception:
                logger.warning(f"Could not parse filing date: {filing_date}")
                continue

            # Check if this is the filing we want
            if form == filing_type and filing_year == year:
                if quarter is None or filing_quarter == quarter:
                    matches.append((filing_date, accession_number))

        if not matches:
            raise Exception(
                f"No {filing_type} filing found for {ticker} in {year}"
                + (f" Q{quarter}" if quarter else "")
            )

        # Sort by date (newest first) and get the accession number
        matches.sort(reverse=True)
        _, accession_number = matches[0]

        # Format the accession number for the URL (remove dashes)
        accession_number_clean = accession_number.replace("-", "")

        # Create the URL for the filing
        cik = self._format_cik(ticker)
        url = f"{self.ARCHIVE_URL}/edgar/data/{int(cik)}/{accession_number_clean}/{accession_number}.txt"
        xbrl_url = f"{self.XBRL_URL.format(cik=cik)}"
        return {
            "url": url,
            "xbrl_url": xbrl_url,
            "accession_number": accession_number,
            "filing_date": date_obj,
        }

    def download_filing(
        self, ticker: str, year: int, quarter: Optional[int], filing_type: str
    ) -> Dict[str, Any]:
        """
        Download a filing from SEC EDGAR.

        Args:
            ticker: Company ticker symbol
            year: Filing year
            quarter: Filing quarter (None for 10-K)
            filing_type: Filing type (10-K or 10-Q)

        Returns:
            Path to the downloaded filing

        Raises:
            Exception: If the filing cannot be found or downloaded
        """

        try:
            # Find the filing URL using the submissions API
            logger.info(
                f"Searching for {filing_type} filing for {ticker} {year}"
                + (f" Q{quarter}" if quarter else "")
            )

            fill_url_data = self.find_filing_url(ticker, year, quarter, filing_type)
            filing_url = fill_url_data["url"]
            filing_date = fill_url_data["filing_date"]
            # Download the index page
            index_response = self._make_request(filing_url)

            # Parse the index page to find the actual document URL
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(index_response.content, "html.parser")

            return {
                "content": soup.prettify(),
                "metadata": DocumentMetadata(
                    document_id=generate_document_id(
                        ticker, year, quarter, filing_type
                    ),
                    ticker=ticker,
                    year=year,
                    quarter=quarter,
                    filing_type=filing_type,
                    filing_date=filing_date,
                ),
            }

        except Exception as e:
            import traceback

            logger.exception(
                f"Error downloading filing: {str(e)} {traceback.format_exc()}"
            )
            raise

    def _format_cik(self, ticker: str) -> str:
        """
        Format CIK number with leading zeros to 10 digits.

        Args:
            ticker: Company ticker symbol

        Returns:
            Formatted CIK number (10 digits with leading zeros)

        Raises:
            Exception: If CIK not found for ticker
        """
        # Check if we already have this ticker in our cache
        if ticker.upper() in self.cik_cache:
            return self.cik_cache[ticker.upper()]

        # Look up the CIK from the SEC API
        try:
            # Use the company_tickers.json endpoint to get CIK numbers
            response = self._make_request(self.TICKER_LOOKUP_URL)
            data = response.json()

            # The API returns a dict where keys are indices and values are company info
            for _, company in data.items():
                if company.get("ticker", "").upper() == ticker.upper():
                    cik = str(company.get("cik_str", ""))
                    logger.info(f"Found CIK {cik} for ticker {ticker}")

                    # Format with leading zeros to 10 digits
                    formatted_cik = cik.zfill(10)

                    # Cache the result
                    self.cik_cache[ticker.upper()] = formatted_cik
                    self._save_cik_cache()

                    return formatted_cik

            # If ticker not found, try the submissions API
            logger.warning(
                f"CIK not found for ticker {ticker} in company_tickers.json, trying full text search"
            )
            raise Exception(f"CIK not found for ticker {ticker}")

        except Exception as e:
            logger.exception(f"Error looking up CIK for ticker {ticker}: {str(e)}")
            raise Exception(f"Error looking up CIK for ticker {ticker}: {str(e)}")

    def _make_request(self, url: str) -> requests.Response:
        """Make a request to the SEC EDGAR API with appropriate headers and rate limiting."""
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov" if "www.sec.gov" in url else "data.sec.gov",
        }

        # Rate limiting - SEC recommends no more than 10 requests per second
        time.sleep(0.1)

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response

    def get_xbrl_facts_url(self, ticker: str) -> requests.Response:
        """
        Get the XBRL facts from the SEC API.

        Args:
            ticker: Company ticker symbol

        Returns:
            Response object containing XBRL company facts

        Raises:
            Exception: If the request fails
        """
        try:
            cik = self._format_cik(ticker)
            xbrl_url = f"{self.XBRL_URL.format(cik=cik)}"
            logger.info(f"Fetching XBRL facts from: {xbrl_url}")

            response = self._make_request(xbrl_url)

            # Save the raw response for debugging
            debug_file = os.path.join(
                self.download_dir, f"{ticker}_xbrl_facts_debug.json"
            )
            with open(debug_file, "w") as f:
                json.dump(response.json(), f, indent=4)
            logger.info(f"Saved raw XBRL data to {debug_file}")

            return response
        except Exception as e:
            logger.error(f"Error getting XBRL facts for {ticker}: {str(e)}")
            raise

    def download_xbrl_facts(self, ticker: str) -> Tuple[List[Fact], List[FactValue]]:
        """
        Download and process XBRL facts from the SEC API.

        This method extracts structured financial data from company filings
        in XBRL format. It processes both facts (metric definitions) and
        fact values (actual data points).

        Args:
            ticker: Company ticker symbol

        Returns:
            Tuple containing:
                - List of Fact objects (financial metric definitions)
                - List of FactValue objects (actual values for those metrics)

        Raises:
            Exception: If the download or processing fails
        """
        try:
            response = self.get_xbrl_facts_url(ticker)
            fact_dict = response.json()

            # Process facts from different taxonomies
            facts = []
            fact_values = []

            # Process each supported taxonomy
            for taxonomy in self.SUPPORTED_TAXONOMIES:
                taxonomy_facts = fact_dict.get("facts", {}).get(taxonomy, {})
                if not taxonomy_facts:
                    logger.info(f"No facts found for taxonomy: {taxonomy}")
                    continue

                logger.info(
                    f"Processing {len(taxonomy_facts)} facts from {taxonomy} taxonomy"
                )

                # Process each fact in the taxonomy
                for concept_name, concept_data in taxonomy_facts.items():
                    # Create the fact object
                    fact_id = f"{taxonomy}:{concept_name}"
                    label = concept_data.get("label", "") or ""
                    description = concept_data.get("description", "") or ""

                    logger.info(f"Processing fact: {fact_id} {label} {description}")

                    # Determine fact type based on units
                    units = concept_data.get("units", {})
                    fact_type = (
                        "monetary"
                        if "USD" in units
                        else "shares"
                        if "shares" in units
                        else "other"
                    )

                    # Create the fact object without embedding
                    fact = Fact(
                        fact_id=fact_id,
                        label=label,
                        description=description,
                        taxonomy=taxonomy,
                        fact_type=fact_type,
                    )

                    # Generate embedding using the unified service
                    # TODO - we dont need to do this every time we download facts. check if the fact already exists in the database.
                    facts.append(fact)

                    # Process fact values for each unit type
                    for unit_type, values in units.items():
                        for value in values:
                            try:
                                # Extract value data
                                val = value.get("val", 0)
                                # filed_date = value.get("filed", "")
                                form = value.get("form", "")
                                accn = value.get("accn", "")
                                fy = value.get("fy", 0)
                                fp = value.get("fp", "")
                                if fp == "FY":
                                    fp = None
                                else:
                                    fp = int(fp.replace("Q", ""))

                                # Handle dates
                                start_date = value.get("start", None)
                                end_date = value.get("end", None)

                                # Map fiscal period

                                # Create a document ID based on available information
                                document_id = generate_document_id(
                                    ticker=ticker, year=fy, quarter=fp, filing_type=form
                                )
                                # Create the fact value object
                                fact_value = FactValue(
                                    fact_id=fact_id,
                                    ticker=ticker,
                                    value=float(val),
                                    document_id=document_id,
                                    filing_type=form,
                                    accession_number=accn,
                                    start_date=start_date,
                                    end_date=end_date,
                                    fiscal_year=fy,
                                    fiscal_period=fp,
                                    unit=unit_type,
                                    form=form,
                                )
                                fact_values.append(fact_value)
                            except Exception as e:
                                logger.warning(
                                    f"Error processing fact value for {fact_id}: {str(e)}"
                                )

            logger.info(
                f"Extracted {len(facts)} facts and {len(fact_values)} fact values for {ticker}"
            )
            self.save_xbrl_facts(ticker, facts)
            self.save_xbrl_fact_values(ticker, fact_values)
            return facts, fact_values
        except Exception as e:
            logger.error(f"Error downloading XBRL facts for {ticker}: {str(e)}")
            raise

    def save_xbrl_facts(self, ticker: str, facts: List[Fact]) -> None:
        """
        Save XBRL facts to the database.

        This method stores the financial metric definitions extracted from XBRL data.
        It performs duplicate checking to avoid storing the same fact multiple times.

        Args:
            ticker: Company ticker symbol
            facts: List of Fact objects to save

        Returns:
            None
        """
        saved_count = 0
        skipped_count = 0
        error_count = 0

        for fact in facts:
            try:
                existing_fact = self.repository.get_fact(fact.fact_id)
                if not existing_fact:
                    fact.embedding = self.embedding_service.embed_fact(fact=fact)
                    self.repository.create_fact(fact)
                    saved_count += 1
                else:
                    if existing_fact.embedding is None:
                        fact.embedding = self.embedding_service.embed_fact(fact=fact)
                        self.repository.update_fact(fact)
                    saved_count += 1
            except Exception as e:
                logger.error(f"Error saving fact {fact.fact_id}: {str(e)}")
                error_count += 1

        logger.info(
            f"Facts for {ticker}: saved {saved_count}, skipped {skipped_count}, errors {error_count}"
        )

    def save_xbrl_fact_values(self, ticker: str, fact_values: List[FactValue]) -> None:
        """
        Save XBRL fact values to the database.

        This method stores the actual financial data points extracted from XBRL data.
        It performs duplicate checking based on the fact ID, document, and dates.

        Args:
            ticker: Company ticker symbol
            fact_values: List of FactValue objects to save

        Returns:
            None
        """
        saved_count = 0
        skipped_count = 0
        error_count = 0

        for fact_value in fact_values:
            try:
                # Check if this fact value already exists
                # Note: A proper implementation would check for duplicates more thoroughly
                existing_value = self.repository.get_fact_value_by_details(
                    fact_value.fact_id,
                    fact_value.ticker,
                    fact_value.fiscal_year,
                    fact_value.fiscal_period,
                    fact_value.filing_type,
                )

                if not existing_value:
                    self.repository.create_fact_value(fact_value)
                    saved_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                logger.error(
                    f"Error saving fact value for {fact_value.fact_id}: {str(e)}"
                )
                error_count += 1

        logger.info(
            f"Fact values for {ticker}: saved {saved_count}, skipped {skipped_count}, errors {error_count}"
        )

    def get_financial_metrics(self, ticker: str, concept: str) -> Dict[str, Any]:
        """
        Get detailed financial metrics for a specific concept.

        Args:
            ticker: Company ticker symbol
            concept: The XBRL concept name (e.g., 'Revenue', 'NetIncome')

        Returns:
            Dictionary containing detailed data for the concept

        Raises:
            Exception: If the request fails
        """
        try:
            cik = self._format_cik(ticker)
            url = f"{self.XBRL_COMPANYCONCEPT_URL.format(cik=cik, concept=concept)}"
            logger.info(f"Fetching data for {concept} from: {url}")

            response = self._make_request(url)
            return response.json()
        except Exception as e:
            logger.error(
                f"Error getting financial metrics for {ticker}/{concept}: {str(e)}"
            )
            raise

    # TODO - is this needed?
    def calculate_derived_metrics(self, ticker: str) -> Dict[str, Any]:
        """
        Calculate derived financial metrics from XBRL data.

        This method computes metrics like growth rates, ratios, and trends
        from the raw financial data stored in the database.

        Args:
            ticker: Company ticker symbol

        Returns:
            Dictionary of derived metrics
        """
        derived_metrics = {}

        try:
            # Get all fact values for this ticker
            fact_values = self.repository.get_fact_values_by_ticker(ticker)

            # Group by fact ID and sort by date
            fact_value_groups = {}
            for fv in fact_values:
                if fv.fact_id not in fact_value_groups:
                    fact_value_groups[fv.fact_id] = []
                fact_value_groups[fv.fact_id].append(fv)

            # Sort each group by fiscal year and period
            for fact_id, values in fact_value_groups.items():
                fact_value_groups[fact_id] = sorted(
                    values,
                    key=lambda fv: (
                        fv.fiscal_year,
                        self._fiscal_period_to_number(fv.fiscal_period),
                    ),
                )

            # Calculate year-over-year growth rates for key metrics
            key_metrics = ["us-gaap:Revenue", "us-gaap:NetIncome", "us-gaap:Assets"]
            for metric in key_metrics:
                if metric in fact_value_groups and len(fact_value_groups[metric]) >= 2:
                    values = fact_value_groups[metric]

                    # Calculate YoY growth
                    for i in range(1, len(values)):
                        if (
                            values[i - 1].value != 0
                            and values[i].fiscal_period == values[i - 1].fiscal_period
                        ):
                            yoy_change = (
                                (values[i].value - values[i - 1].value)
                                / abs(values[i - 1].value)
                                * 100
                            )
                            key = f"{metric}_YoY_{values[i].fiscal_year}_{values[i].fiscal_period}"
                            derived_metrics[key] = yoy_change

            # Calculate key financial ratios
            revenue_values = fact_value_groups.get("us-gaap:Revenue", [])
            net_income_values = fact_value_groups.get("us-gaap:NetIncome", [])

            # Calculate profit margin for each matching period
            for rev in revenue_values:
                for ni in net_income_values:
                    if (
                        rev.fiscal_year == ni.fiscal_year
                        and rev.fiscal_period == ni.fiscal_period
                        and rev.value != 0
                    ):
                        profit_margin = (ni.value / rev.value) * 100
                        key = f"ProfitMargin_{rev.fiscal_year}_{rev.fiscal_period}"
                        derived_metrics[key] = profit_margin

            logger.info(
                f"Calculated {len(derived_metrics)} derived metrics for {ticker}"
            )
            return derived_metrics
        except Exception as e:
            logger.error(f"Error calculating derived metrics for {ticker}: {str(e)}")
            return {}

    def _fiscal_period_to_number(self, fp: str) -> int:
        """Convert fiscal period to a numeric value for sorting."""
        if fp == "FY":
            return 5
        elif fp.startswith("Q") and len(fp) > 1:
            try:
                return int(fp[1:])
            except:
                return 0
        return 0

    def find_xbrl_fact_locations(self, ticker, document_id):
        """Locate XBRL facts in the document by parsing the iXBRL content."""
        # Get the document content
        document = self.repository.get_document(document_id)
        if not document or not document.content:
            return {}

        # Parse the document as HTML/iXBRL
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(document.content, "html.parser")

        # Find all iXBRL tags
        ixbrl_elements = soup.find_all(
            attrs={"name": lambda x: x and x.startswith("ix:")}
        )
        fact_locations = {}

        # Extract fact information and locations
        for element in ixbrl_elements:
            fact_name = element.get("name")
            if not fact_name:
                continue

            # Get taxonomy and concept info
            if ":" in fact_name:
                taxonomy, concept = fact_name.split(":", 1)
                fact_id = f"{taxonomy}:{concept}"

                # Store location info (you could get more precise with char offsets)
                fact_locations[fact_id] = {
                    "element_id": element.get("id", ""),
                    "context_ref": element.get("contextref", ""),
                    "value": element.text.strip(),
                    "parent_element": element.parent.name,
                }

        return fact_locations
