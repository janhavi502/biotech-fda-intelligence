import requests
import json
import os

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

def search_pubmed(term, max_results=5):
    print(f"Searching PubMed for: {term}")
    url = f"{BASE_URL}/esearch.fcgi?db=pubmed&term={term}&retmax={max_results}&retmode=json"
    response = requests.get(url)
    assert response.status_code == 200, f"Failed: {response.status_code}"
    data = response.json()
    ids = data["esearchresult"]["idlist"]
    total = data["esearchresult"]["count"]
    print(f"Total articles found: {total}")
    print(f"Sample PMIDs: {ids}")
    return ids

def fetch_pubmed_details(pmids):
    print("\nFetching article details...")
    ids_str = ",".join(pmids)
    url = f"{BASE_URL}/esummary.fcgi?db=pubmed&id={ids_str}&retmode=json"
    response = requests.get(url)
    assert response.status_code == 200, f"Failed: {response.status_code}"
    data = response.json()
    articles = data["result"]
    for pmid in pmids[:2]:
        article = articles.get(pmid, {})
        print(f"Title: {article.get('title', 'N/A')[:100]}")
        print(f"Published: {article.get('pubdate', 'N/A')}")
        print("---")
    return data

def save_output(data, filename):
    os.makedirs("sample_outputs", exist_ok=True)
    with open(f"sample_outputs/{filename}", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved to sample_outputs/{filename}")

if __name__ == "__main__":
    pmids = search_pubmed("biotech+FDA+approval+oncology")
    details = fetch_pubmed_details(pmids)

    save_output({
        "pmids": pmids,
        "articles": {k: details["result"][k] for k in pmids[:2] if k in details["result"]}
    }, "pubmed_sample.json")

    print("\nAll PubMed tests passed.")