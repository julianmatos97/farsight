"""Client for downloading 10-K/10-Q filings from the SEC EDGAR database."""

import logging
import requests
import time
from typing import Optional, Dict, Any, List, Tuple
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class EdgarClient:
    """Client for downloading 10-K/10-Q filings from the SEC EDGAR database."""
    
    ARCHIVE_URL = "https://www.sec.gov/Archives"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions"
    TICKER_LOOKUP_URL = "https://www.sec.gov/files/company_tickers.json"
    USER_AGENT = "Farsight2/0.1.0 (contact@example.com)"  # Replace with your contact info
    
    def __init__(self, download_dir: Optional[str] = None):
        """Initialize the EDGAR client.
        
        Args:
            download_dir: Directory to save downloaded files. Defaults to data/downloads.
        """
        self.download_dir = download_dir or os.path.join(os.path.dirname(__file__), "../../data/downloads")
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Cache for CIK lookups to minimize API calls
        self.cik_cache = {}
        self._load_cik_cache()
    
    def _load_cik_cache(self):
        """Load CIK cache from file if it exists."""
        cache_file = os.path.join(self.download_dir, "cik_cache.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    self.cik_cache = json.load(f)
                logger.info(f"Loaded {len(self.cik_cache)} CIKs from cache")
            except Exception as e:
                logger.warning(f"Failed to load CIK cache: {e}")
    
    def _save_cik_cache(self):
        """Save CIK cache to file."""
        cache_file = os.path.join(self.download_dir, "cik_cache.json")
        try:
            with open(cache_file, 'w') as f:
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

        logger.info(f"Fetched company filings: {data}")
        
        # Cache the CIK if we found it
        if data and not ticker.upper() in self.cik_cache:
            self.cik_cache[ticker.upper()] = cik
            self._save_cik_cache()
            
        return data
    
    def find_filing_url(self, ticker: str, year: int, quarter: Optional[int], filing_type: str) -> str:
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
        form_array = recent_filings.get("fillings", [])
        filing_date_array = recent_filings.get("filingDate", [])
        accession_number_array = recent_filings.get("accessionNumber", [])
        
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
            raise Exception(f"No {filing_type} filing found for {ticker} in {year}" + 
                           (f" Q{quarter}" if quarter else ""))
        
        # Sort by date (newest first) and get the accession number
        matches.sort(reverse=True)
        _, accession_number = matches[0]
        
        # Format the accession number for the URL (remove dashes)
        accession_number_clean = accession_number.replace("-", "")
        
        # Create the URL for the filing
        cik = self._format_cik(ticker)
        url = f"{self.ARCHIVE_URL}/edgar/data/{int(cik)}/{accession_number_clean}/{accession_number}-index.html"
        
        return url
    
    def download_filing(self, ticker: str, year: int, quarter: Optional[int], filing_type: str) -> str:
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
        # Create filing-specific directory
        filing_dir = os.path.join(self.download_dir, ticker)
        os.makedirs(filing_dir, exist_ok=True)
        
        # Determine the output path
        if quarter:
            output_path = os.path.join(filing_dir, f"{ticker}_{filing_type}_{year}_Q{quarter}.html")
        else:
            output_path = os.path.join(filing_dir, f"{ticker}_{filing_type}_{year}.html")
        
        # If the file already exists, return the path
        if os.path.exists(output_path):
            logger.info(f"Filing already downloaded: {output_path}")
            return output_path
        
        try:
            # Find the filing URL using the submissions API
            logger.info(f"Searching for {filing_type} filing for {ticker} {year}" + 
                       (f" Q{quarter}" if quarter else ""))
            
            filing_index_url = self.find_filing_url(ticker, year, quarter, filing_type)
            
            # Download the index page
            index_response = self._make_request(filing_index_url)
            
            # Parse the index page to find the actual document URL
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(index_response.content, 'html.parser')
            
            # Find the document table
            doc_table = soup.find('table', summary='Document Format Files')
            if not doc_table:
                raise Exception(f"Could not find document table in index page: {filing_index_url}")
            
            # Find the HTML document link
            doc_link = None
            logger.info(f"Searching for {filing_type} document in table with {len(doc_table.find_all('tr'))} rows")
            for row in doc_table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 3:
                    doc_type = cells[0].get_text().strip()
                    doc_description = cells[1].get_text().strip()
                    
                    logger.debug(f"Found document: type={doc_type}, description={doc_description}")
                    
                    if ('10-K' in doc_type or '10-Q' in doc_type) and \
                       ('html' in doc_description.lower() or 
                        'htm' in doc_description.lower() or 
                        cells[2].find('a', href=True)):
                        doc_link = cells[2].find('a', href=True)
                        logger.info(f"Found matching document: {doc_type} - {doc_description}")
                        break
            
            if not doc_link or not doc_link.get('href'):
                raise Exception(f"Could not find document link in index page: {filing_index_url}")
            
            # Construct the document URL
            doc_url = "https://www.sec.gov" + doc_link['href']
            
            # Download the document
            logger.info(f"Downloading filing from {doc_url}")
            doc_response = self._make_request(doc_url)
            
            # Save the filing
            with open(output_path, "wb") as f:
                f.write(doc_response.content)
            
            logger.info(f"Filing downloaded to {output_path}")
            return output_path
            
        except Exception as e:
            logger.exception(f"Error downloading filing: {str(e)}")
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
                if company.get('ticker', '').upper() == ticker.upper():
                    cik = str(company.get('cik_str', ''))
                    logger.info(f"Found CIK {cik} for ticker {ticker}")
                    
                    # Format with leading zeros to 10 digits
                    formatted_cik = cik.zfill(10)
                    
                    # Cache the result
                    self.cik_cache[ticker.upper()] = formatted_cik
                    self._save_cik_cache()
                    
                    return formatted_cik
            
            # If ticker not found, try the submissions API
            logger.warning(f"CIK not found for ticker {ticker} in company_tickers.json, trying full text search")
            raise Exception(f"CIK not found for ticker {ticker}")
            
        except Exception as e:
            logger.exception(f"Error looking up CIK for ticker {ticker}: {str(e)}")
            raise Exception(f"Error looking up CIK for ticker {ticker}: {str(e)}")
    
    def _make_request(self, url: str) -> requests.Response:
        """Make a request to the SEC EDGAR API with appropriate headers and rate limiting."""
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov" if "www.sec.gov" in url else "data.sec.gov"
        }
        
        # Rate limiting - SEC recommends no more than 10 requests per second
        time.sleep(0.1)
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response 