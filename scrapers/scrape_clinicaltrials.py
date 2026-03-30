"""
ClinicalTrials.gov Data Scraper
Fetches clinical trial records via the ClinicalTrials.gov v2 REST API.
Saves structured trial data as JSON and Markdown files.
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

BASE_URL = "https://clinicaltrials.gov/api/v2"
OUTPUT_DIR = "raw_data/clinicaltrials"
REQUEST_DELAY = 0.5
BATCH_SIZE = 100
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
                logger.error(f"HTTP {response.status_code} | attempt {attempt}/{retries}")
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


def save_markdown(trials: list, folder: str, filename: str):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        for i, trial in enumerate(trials, 1):
            f.write(f"## Trial {i}: {trial.get('brief_title', 'No Title')}\n\n")
            f.write(f"**NCT ID**: {trial.get('nct_id', 'N/A')}\n")
            f.write(f"**Status**: {trial.get('overall_status', 'N/A')}\n")
            f.write(f"**Phase**: {trial.get('phase', 'N/A')}\n")
            f.write(f"**Condition**: {trial.get('conditions', 'N/A')}\n")
            f.write(f"**Interventions**: {trial.get('interventions', 'N/A')}\n")
            f.write(f"**Sponsor**: {trial.get('lead_sponsor', 'N/A')}\n")
            f.write(f"**Start Date**: {trial.get('start_date', 'N/A')}\n")
            f.write(f"**Completion Date**: {trial.get('completion_date', 'N/A')}\n")
            f.write(f"**Enrollment**: {trial.get('enrollment', 'N/A')}\n")
            f.write(f"**URL**: https://clinicaltrials.gov/study/{trial.get('nct_id', '')}\n\n")
            if trial.get("brief_summary"):
                f.write(f"**Summary**: {trial['brief_summary']}\n\n")
            f.write("---\n\n")
    logger.info(f"Saved markdown to {filepath}")

# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_trial(study: dict) -> dict:
    """Extract relevant fields from a raw ClinicalTrials API study record."""
    protocol = study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    status = protocol.get("statusModule", {})
    description = protocol.get("descriptionModule", {})
    design = protocol.get("designModule", {})
    conditions_module = protocol.get("conditionsModule", {})
    interventions_module = protocol.get("armsInterventionsModule", {})
    sponsor_module = protocol.get("sponsorCollaboratorsModule", {})

    interventions = [
        i.get("name", "") for i in interventions_module.get("interventions", [])
    ]

    return {
        "nct_id": identification.get("nctId", ""),
        "brief_title": identification.get("briefTitle", ""),
        "official_title": identification.get("officialTitle", ""),
        "overall_status": status.get("overallStatus", ""),
        "start_date": status.get("startDateStruct", {}).get("date", ""),
        "completion_date": status.get("completionDateStruct", {}).get("date", ""),
        "phase": ", ".join(design.get("phases", [])),
        "enrollment": design.get("enrollmentInfo", {}).get("count", ""),
        "conditions": ", ".join(conditions_module.get("conditions", [])),
        "interventions": ", ".join(interventions),
        "lead_sponsor": sponsor_module.get("leadSponsor", {}).get("name", ""),
        "brief_summary": description.get("briefSummary", ""),
        "url": f"https://clinicaltrials.gov/study/{identification.get('nctId', '')}"
    }

# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

def scrape_trials(query: str, total_records: int = 1000) -> list:
    """
    Scrape clinical trials for a given search query.
    Paginates using nextPageToken from the API response.
    """
    logger.info(f"Scraping trials for: '{query}' | target: {total_records} records")
    all_trials = []
    next_page_token = None

    while len(all_trials) < total_records:
        batch = min(BATCH_SIZE, total_records - len(all_trials))
        url = (
            f"{BASE_URL}/studies"
            f"?query.term={query}"
            f"&pageSize={batch}"
            f"&format=json"
        )
        if next_page_token:
            url += f"&pageToken={next_page_token}"

        data = make_request(url)
        studies = data.get("studies", [])
        if not studies:
            logger.info("No more studies returned.")
            break

        for study in studies:
            all_trials.append(parse_trial(study))

        next_page_token = data.get("nextPageToken")
        logger.info(f"Collected {len(all_trials)} trials so far")

        if not next_page_token:
            logger.info("Reached last page of results.")
            break

        time.sleep(REQUEST_DELAY)

    return all_trials

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    today = datetime.today().strftime("%Y-%m-%d")

    search_queries = [
        "biotech+cancer+immunotherapy",
        "mRNA+vaccine+clinical+trial",
        "oncology+phase+3+FDA",
        "targeted+therapy+biomarker+driven",
        "biologics+clinical+trial+recruiting"
    ]

    all_trials = []
    for query in search_queries:
        trials = scrape_trials(query=query, total_records=500)
        all_trials.extend(trials)

    # deduplicate by NCT ID
    seen = set()
    unique_trials = []
    for t in all_trials:
        if t["nct_id"] not in seen:
            seen.add(t["nct_id"])
            unique_trials.append(t)

    logger.info(f"Total unique trials after deduplication: {len(unique_trials)}")

    output_folder = os.path.join(OUTPUT_DIR, today)
    save_json(unique_trials, output_folder, "clinical_trials.json")
    save_markdown(unique_trials, output_folder, "clinical_trials.md")

    logger.info("ClinicalTrials scraping complete.")


if __name__ == "__main__":
    main()