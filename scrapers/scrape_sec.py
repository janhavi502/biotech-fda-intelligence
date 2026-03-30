"""
SEC EDGAR Data Scraper
Fetches 10-K, 10-Q, and 8-K filings for biotech companies via SEC EDGAR REST API.
Saves filing metadata and raw text as JSON and Markdown files.
"""

import requests
import json
import os
import time
import logging
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://data.sec.gov"
OUTPUT_DIR = "raw_data/sec"
REQUEST_DELAY = 0.15      # SEC asks for max 10 requests/second
MAX_RETRIES = 3

# User-Agent is required by SEC — must include name and email
HEADERS = {
    "User-Agent": "biotech-fda-intelligence patil.janhavi@northeastern.edu",
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov"
}

# Target biotech companies with verified CIK numbers
BIOTECH_COMPANIES = {
    "Moderna":    "0001682852",
    "BioNTech":   "0001776985",
    "Regeneron":  "0000872589",
    "Biogen":     "0000875045",
    "Gilead":     "0000882184",
    "Amgen":      "0000019617",
    "Vertex":     "0000875320",
    "Illumina":   "0001110803",
    "Seagen":     "0001060349",
    "Incyte":     "0000879169"
}

TARGET_FORM_TYPES = {"10-K", "10-Q", "8-K"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core utilities
# ---------------------------------------------------------------------------

def make_request(url: str, retries: int = MAX_RETRIES) -> dict:
    """Make a GET request with retry logic."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"Rate limited. Waiting {wait}s before retry {attempt}/{retries}")
                time.sleep(wait)
            else:
                logger.error(f"HTTP {response.status_code} | attempt {attempt}/{retries} | {url}")
                time.sleep(2)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error (attempt {attempt}/{retries}): {e}")
            time.sleep(2)
    return {}


def save_json(data: list, folder: str, filename: str):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved {len(data)} records to {filepath}")


def save_markdown(filings: list, folder: str, filename: str):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        for i, filing in enumerate(filings, 1):
            f.write(f"## Filing {i}: {filing.get('company', 'N/A')} - {filing.get('form_type', 'N/A')}\n\n")
            f.write(f"**Company**: {filing.get('company', 'N/A')}\n")
            f.write(f"**Ticker**: {filing.get('ticker', 'N/A')}\n")
            f.write(f"**CIK**: {filing.get('cik', 'N/A')}\n")
            f.write(f"**Form Type**: {filing.get('form_type', 'N/A')}\n")
            f.write(f"**Filed Date**: {filing.get('filing_date', 'N/A')}\n")
            f.write(f"**Accession Number**: {filing.get('accession_number', 'N/A')}\n")
            f.write(f"**Document URL**: {filing.get('document_url', 'N/A')}\n\n")
            f.write("---\n\n")
    logger.info(f"Saved markdown to {filepath}")

# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

def fetch_company_filings(company: str, cik: str, max_filings: int = 100) -> list:
    """
    Fetch recent filings for a company filtered by target form types.
    Returns a list of structured filing metadata records.
    """
    logger.info(f"Fetching filings for {company} (CIK: {cik})")
    url = f"{BASE_URL}/submissions/CIK{cik}.json"
    data = make_request(url)

    if not data:
        logger.warning(f"No data returned for {company}")
        return []

    company_name = data.get("name", company)
    tickers = data.get("tickers", [])
    ticker = tickers[0] if tickers else "N/A"

    recent = data.get("filings", {}).get("recent", {})
    form_types = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])

    filings = []
    for form, date, accession in zip(form_types, filing_dates, accession_numbers):
        if form in TARGET_FORM_TYPES:
            accession_clean = accession.replace("-", "")
            doc_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{int(cik)}/{accession_clean}/{accession}.txt"
            )
            filings.append({
                "company": company_name,
                "ticker": ticker,
                "cik": cik,
                "form_type": form,
                "filing_date": date,
                "accession_number": accession,
                "document_url": doc_url
            })

        if len(filings) >= max_filings:
            break

    logger.info(f"Found {len(filings)} target filings for {company}")
    return filings

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    today = datetime.today().strftime("%Y-%m-%d")
    all_filings = []

    for company, cik in BIOTECH_COMPANIES.items():
        filings = fetch_company_filings(company=company, cik=cik, max_filings=100)
        all_filings.extend(filings)
        time.sleep(REQUEST_DELAY)

    logger.info(f"Total filings collected: {len(all_filings)}")

    output_folder = os.path.join(OUTPUT_DIR, today)
    save_json(all_filings, output_folder, "sec_filings.json")
    save_markdown(all_filings, output_folder, "sec_filings.md")

    # also save a summary per company
    summary = {}
    for filing in all_filings:
        co = filing["company"]
        if co not in summary:
            summary[co] = {"ticker": filing["ticker"], "filings": []}
        summary[co]["filings"].append({
            "form": filing["form_type"],
            "date": filing["filing_date"]
        })

    summary_path = os.path.join(output_folder, "company_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Saved company summary to {summary_path}")

    logger.info("SEC EDGAR scraping complete.")


if __name__ == "__main__":
    main()