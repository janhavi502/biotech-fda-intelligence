"""
FDA Data Scraper
Pulls drug adverse events, approvals, and recalls from OpenFDA API.
Saves raw records as JSON files partitioned by date.
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

BASE_URL = "https://api.fda.gov"
OUTPUT_DIR = "raw_data/fda"
REQUEST_DELAY = 0.5       # seconds between requests to respect rate limits
MAX_RETRIES = 3
BATCH_SIZE = 100          # max allowed per OpenFDA request

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
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"Rate limited. Waiting {wait}s before retry {attempt}/{retries}")
                time.sleep(wait)
            else:
                logger.error(f"HTTP {response.status_code} for URL: {url}")
                return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed (attempt {attempt}/{retries}): {e}")
            time.sleep(2)
    return {}


def save_json(data: list, folder: str, filename: str):
    """Save a list of records to a JSON file."""
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved {len(data)} records to {filepath}")


def save_markdown(records: list, folder: str, filename: str, fields: list):
    """Save records as a markdown file for LLM ingestion."""
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        for i, record in enumerate(records, 1):
            f.write(f"## Record {i}\n")
            for field in fields:
                value = record.get(field, "N/A")
                f.write(f"**{field}**: {value}\n")
            f.write("\n---\n\n")
    logger.info(f"Saved markdown to {filepath}")

# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def scrape_adverse_events(drug_term: str, total_records: int = 1000) -> list:
    """
    Scrape drug adverse event reports for a given search term.
    Paginates through results in batches.
    """
    logger.info(f"Scraping adverse events for: {drug_term} | target: {total_records} records")
    all_records = []
    skip = 0

    while len(all_records) < total_records:
        batch = min(BATCH_SIZE, total_records - len(all_records))
        url = (
            f"{BASE_URL}/drug/event.json"
            f"?search={drug_term}"
            f"&limit={batch}"
            f"&skip={skip}"
        )
        data = make_request(url)
        results = data.get("results", [])
        if not results:
            logger.info("No more records available.")
            break

        all_records.extend(results)
        skip += batch
        logger.info(f"Fetched {len(all_records)} / {total_records} adverse event records")
        time.sleep(REQUEST_DELAY)

    return all_records


def scrape_drug_approvals(search_term: str, total_records: int = 500) -> list:
    """
    Scrape FDA drug approval records (Drugs@FDA).
    """
    logger.info(f"Scraping drug approvals for: {search_term} | target: {total_records} records")
    all_records = []
    skip = 0

    while len(all_records) < total_records:
        batch = min(BATCH_SIZE, total_records - len(all_records))
        url = (
            f"{BASE_URL}/drug/drugsfda.json"
            f"?search={search_term}"
            f"&limit={batch}"
            f"&skip={skip}"
        )
        data = make_request(url)
        results = data.get("results", [])
        if not results:
            logger.info("No more approval records available.")
            break

        all_records.extend(results)
        skip += batch
        logger.info(f"Fetched {len(all_records)} approval records so far")
        time.sleep(REQUEST_DELAY)

    return all_records


def scrape_drug_recalls(total_records: int = 1000) -> list:
    """
    Scrape FDA drug recall enforcement records.
    """
    logger.info(f"Scraping drug recalls | target: {total_records} records")
    all_records = []
    skip = 0

    while len(all_records) < total_records:
        batch = min(BATCH_SIZE, total_records - len(all_records))
        url = (
            f"{BASE_URL}/drug/enforcement.json"
            f"?limit={batch}"
            f"&skip={skip}"
        )
        data = make_request(url)
        results = data.get("results", [])
        if not results:
            logger.info("No more recall records available.")
            break

        all_records.extend(results)
        skip += batch
        logger.info(f"Fetched {len(all_records)} recall records so far")
        time.sleep(REQUEST_DELAY)

    return all_records

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    today = datetime.today().strftime("%Y-%m-%d")

    # --- Adverse Events ---
    search_terms = ["cancer", "oncology", "biotech", "immunotherapy"]
    all_adverse = []
    for term in search_terms:
        records = scrape_adverse_events(drug_term=term, total_records=500)
        all_adverse.extend(records)

    adverse_folder = os.path.join(OUTPUT_DIR, "adverse_events", today)
    save_json(all_adverse, adverse_folder, "adverse_events.json")
    save_markdown(
        all_adverse[:200],
        adverse_folder,
        "adverse_events.md",
        fields=["safetyreportid", "receivedate", "primarysourcecountry", "serious"]
    )

    # --- Drug Approvals ---
    approval_terms = ["oncology", "immunotherapy", "biologics"]
    all_approvals = []
    for term in approval_terms:
        records = scrape_drug_approvals(search_term=term, total_records=300)
        all_approvals.extend(records)

    approval_folder = os.path.join(OUTPUT_DIR, "approvals", today)
    save_json(all_approvals, approval_folder, "drug_approvals.json")
    save_markdown(
        all_approvals[:100],
        approval_folder,
        "drug_approvals.md",
        fields=["application_number", "sponsor_name", "products"]
    )

    # --- Drug Recalls ---
    recalls = scrape_drug_recalls(total_records=1000)
    recall_folder = os.path.join(OUTPUT_DIR, "recalls", today)
    save_json(recalls, recall_folder, "drug_recalls.json")
    save_markdown(
        recalls[:200],
        recall_folder,
        "drug_recalls.md",
        fields=["recall_number", "recalling_firm", "reason_for_recall", "status", "recall_initiation_date"]
    )

    logger.info("FDA scraping complete.")


if __name__ == "__main__":
    main()