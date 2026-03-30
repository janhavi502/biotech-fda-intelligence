import requests
import json
import os

BASE_URL = "https://data.sec.gov"
HEADERS = {"User-Agent": "biotech-fda-intelligence patil.janhavi@northeastern.edu"}

# CIK numbers for major biotech companies
BIOTECH_CIKS = {
    "Moderna": "0001682852",
    "BioNTech": "0001776985",
    "Regeneron": "0000872589"
}

def test_company_filings(company_name, cik):
    print(f"Fetching SEC filings for {company_name}...")
    url = f"{BASE_URL}/submissions/CIK{cik}.json"
    response = requests.get(url, headers=HEADERS)
    assert response.status_code == 200, f"Failed: {response.status_code}"
    data = response.json()
    print(f"Company: {data.get('name', 'N/A')}")
    tickers = data.get('tickers', [])
    print(f"Ticker: {tickers[0] if tickers else 'N/A'}")
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    print(f"Total recent filings: {len(forms)}")
    for i, (form, date) in enumerate(zip(forms[:5], dates[:5])):
        print(f"  {date} - {form}")
    return data

def test_company_facts(cik):
    print("\nFetching company financial facts...")
    url = f"{BASE_URL}/api/xbrl/companyfacts/CIK{cik}.json"
    response = requests.get(url, headers=HEADERS)
    assert response.status_code == 200, f"Failed: {response.status_code}"
    data = response.json()
    facts = data.get("facts", {}).get("us-gaap", {})
    print(f"Available financial metrics: {list(facts.keys())[:5]}")
    return data

def save_output(data, filename):
    os.makedirs("sample_outputs", exist_ok=True)
    with open(f"sample_outputs/{filename}", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved to sample_outputs/{filename}")

if __name__ == "__main__":
    results = {}
    for company, cik in BIOTECH_CIKS.items():
        filing_data = test_company_filings(company, cik)
        results[company] = {
            "name": filing_data.get("name"),
            "ticker": filing_data.get("tickers", []),
            "recent_filings": list(zip(
                filing_data["filings"]["recent"]["form"][:5],
                filing_data["filings"]["recent"]["filingDate"][:5]
            ))
        }
        print("---")

    save_output(results, "sec_sample.json")
    print("\nAll SEC EDGAR tests passed.")