import requests
import json
import os

BASE_URL = "https://api.fda.gov"

def test_drug_adverse_events():
    print("Testing FDA Drug Adverse Events...")
    url = f"{BASE_URL}/drug/event.json?search=cancer&limit=5"
    response = requests.get(url)
    assert response.status_code == 200, f"Failed: {response.status_code}"
    data = response.json()
    print(f"Total records available: {data['meta']['results']['total']}")
    print(f"Sample record keys: {list(data['results'][0].keys())}")
    return data

def test_drug_approvals():
    print("\nTesting FDA Drug Approvals...")
    url = f"{BASE_URL}/drug/drugsfda.json?search=oncology&limit=5"
    response = requests.get(url)
    assert response.status_code == 200, f"Failed: {response.status_code}"
    data = response.json()
    print(f"Total approvals available: {data['meta']['results']['total']}")
    print(f"Sample approval: {data['results'][0].get('openfda', {}).get('brand_name', 'N/A')}")
    return data

def test_drug_recalls():
    print("\nTesting FDA Drug Recalls...")
    url = f"{BASE_URL}/drug/enforcement.json?limit=5"
    response = requests.get(url)
    assert response.status_code == 200, f"Failed: {response.status_code}"
    data = response.json()
    print(f"Total recall records available: {data['meta']['results']['total']}")
    print(f"Sample recall reason: {data['results'][0].get('reason_for_recall', 'N/A')[:100]}")
    return data

def save_output(data, filename):
    os.makedirs("sample_outputs", exist_ok=True)
    with open(f"sample_outputs/{filename}", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved to sample_outputs/{filename}")

if __name__ == "__main__":
    adverse_data = test_drug_adverse_events()
    approval_data = test_drug_approvals()
    recall_data = test_drug_recalls()

    save_output({
        "adverse_events": adverse_data["results"][:2],
        "approvals": approval_data["results"][:2],
        "recalls": recall_data["results"][:2]
    }, "fda_sample.json")

    print("\nAll FDA tests passed.")