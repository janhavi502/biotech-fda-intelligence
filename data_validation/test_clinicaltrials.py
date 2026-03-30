import requests
import json
import os

BASE_URL = "https://clinicaltrials.gov/api/v2"

def test_search_trials():
    print("Searching ClinicalTrials.gov...")
    url = f"{BASE_URL}/studies?query.term=biotech+cancer&pageSize=5&format=json"
    response = requests.get(url)
    assert response.status_code == 200, f"Failed: {response.status_code}"
    data = response.json()
    studies = data.get("studies", [])
    print(f"Studies returned: {len(studies)}")
    for s in studies[:2]:
        info = s.get("protocolSection", {}).get("identificationModule", {})
        status = s.get("protocolSection", {}).get("statusModule", {})
        print(f"Trial ID: {info.get('nctId', 'N/A')}")
        print(f"Title: {info.get('briefTitle', 'N/A')[:100]}")
        print(f"Status: {status.get('overallStatus', 'N/A')}")
        print("---")
    return data

def test_single_trial():
    print("Fetching a single trial record...")
    # NCT04470427 - Moderna mRNA-1273 Phase 3 trial
    url = f"{BASE_URL}/studies/NCT04470427?format=json"
    response = requests.get(url)
    assert response.status_code == 200, f"Failed: {response.status_code}"
    data = response.json()
    info = data.get("protocolSection", {}).get("identificationModule", {})
    print(f"Trial: {info.get('briefTitle', 'N/A')}")
    print(f"NCT ID: {info.get('nctId', 'N/A')}")
    return data

def save_output(data, filename):
    os.makedirs("sample_outputs", exist_ok=True)
    with open(f"sample_outputs/{filename}", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved to sample_outputs/{filename}")

if __name__ == "__main__":
    search_data = test_search_trials()
    single_data = test_single_trial()

    save_output({
        "search_results": search_data.get("studies", [])[:2],
        "single_trial": single_data
    }, "clinicaltrials_sample.json")

    print("\nAll ClinicalTrials tests passed.")