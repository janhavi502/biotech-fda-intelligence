"""
PubMed Data Scraper
Searches and fetches biomedical research articles via NCBI E-utilities API.
Saves article metadata and abstracts as JSON and Markdown files.
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

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OUTPUT_DIR = "raw_data/pubmed"
REQUEST_DELAY = 0.4       # NCBI allows 3 requests/second without API key
BATCH_SIZE = 100          # max records per EFetch call
MAX_RETRIES = 3

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


def save_markdown(articles: list, folder: str, filename: str):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        for i, article in enumerate(articles, 1):
            f.write(f"## Article {i}: {article.get('title', 'No Title')}\n\n")
            f.write(f"**PMID**: {article.get('pmid', 'N/A')}\n")
            f.write(f"**Published**: {article.get('pubdate', 'N/A')}\n")
            f.write(f"**Authors**: {', '.join(article.get('authors', []))}\n")
            f.write(f"**Journal**: {article.get('fulljournalname', 'N/A')}\n")
            f.write(f"**Source**: https://pubmed.ncbi.nlm.nih.gov/{article.get('pmid', '')}/\n\n")
            f.write("---\n\n")
    logger.info(f"Saved markdown to {filepath}")

# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def search_pubmed(query: str, max_results: int = 1000) -> list:
    """
    Search PubMed for a query term and return a list of PMIDs.
    Paginates using retstart parameter.
    """
    logger.info(f"Searching PubMed: '{query}' | target: {max_results} PMIDs")
    all_pmids = []
    retstart = 0

    while len(all_pmids) < max_results:
        batch = min(BATCH_SIZE, max_results - len(all_pmids))
        url = (
            f"{BASE_URL}/esearch.fcgi"
            f"?db=pubmed"
            f"&term={query}"
            f"&retmax={batch}"
            f"&retstart={retstart}"
            f"&retmode=json"
        )
        data = make_request(url)
        pmids = data.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            logger.info("No more PMIDs returned.")
            break

        all_pmids.extend(pmids)
        retstart += batch
        logger.info(f"Collected {len(all_pmids)} PMIDs so far")
        time.sleep(REQUEST_DELAY)

    return all_pmids


def fetch_article_details(pmids: list) -> list:
    """
    Fetch article metadata for a list of PMIDs using ESummary.
    Processes in batches to stay within API limits.
    """
    logger.info(f"Fetching details for {len(pmids)} articles")
    all_articles = []

    for i in range(0, len(pmids), BATCH_SIZE):
        batch = pmids[i:i + BATCH_SIZE]
        ids_str = ",".join(batch)
        url = (
            f"{BASE_URL}/esummary.fcgi"
            f"?db=pubmed"
            f"&id={ids_str}"
            f"&retmode=json"
        )
        data = make_request(url)
        result = data.get("result", {})

        for pmid in batch:
            article = result.get(pmid, {})
            if article:
                all_articles.append({
                    "pmid": pmid,
                    "title": article.get("title", ""),
                    "pubdate": article.get("pubdate", ""),
                    "fulljournalname": article.get("fulljournalname", ""),
                    "authors": [
                        a.get("name", "") for a in article.get("authors", [])
                    ],
                    "source": article.get("source", ""),
                    "doi": article.get("elocationid", ""),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                })

        logger.info(f"Processed batch {i // BATCH_SIZE + 1} | total articles: {len(all_articles)}")
        time.sleep(REQUEST_DELAY)

    return all_articles

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    today = datetime.today().strftime("%Y-%m-%d")

    search_queries = [
        "biotech+FDA+approval+oncology",
        "clinical+trial+immunotherapy+results",
        "drug+approval+adverse+events+biomarker",
        "mRNA+vaccine+phase+3+trial",
        "cancer+targeted+therapy+clinical+outcomes"
    ]

    all_pmids = []
    for query in search_queries:
        pmids = search_pubmed(query=query, max_results=500)
        all_pmids.extend(pmids)

    # deduplicate
    unique_pmids = list(dict.fromkeys(all_pmids))
    logger.info(f"Total unique PMIDs after deduplication: {len(unique_pmids)}")

    articles = fetch_article_details(unique_pmids)

    output_folder = os.path.join(OUTPUT_DIR, today)
    save_json(articles, output_folder, "pubmed_articles.json")
    save_markdown(articles, output_folder, "pubmed_articles.md")

    logger.info("PubMed scraping complete.")


if __name__ == "__main__":
    main()