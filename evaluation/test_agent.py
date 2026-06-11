import json
from pathlib import Path

import requests

API_URL = "http://127.0.0.1:8000/api/v1/agent/answer"

TEST_DATASET_PATH = Path("../data/test/test_dataset.json")
OUTPUT_PATH = Path("predicted_set.json")


def load_test_cases():
    with open(TEST_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_agent_predictions():
    test_cases = load_test_cases()
    predicted_set = []

    for case in test_cases[27:]:
        response = requests.post(
            API_URL,
            json={"text": case["review"]},
            timeout=60
        )

        assert response.status_code == 200, response.text

        data = response.json()

        assert isinstance(data, dict)
        assert "intent" in data
        assert "urgency" in data
        assert "requires_human" in data
        assert "routed_team" in data

        predicted_set.append({
            "review": case["review"],
            "intent": data.get("intent"),
            "urgency": data.get("urgency"),
            "requires_human": data.get("requires_human"),
            "routed_team": data.get("routed_team"),
            "draft_response_ar": data.get("draft_response_ar"),
            "latency_ms": data.get("latency_ms"),
            "est_cost_usd": data.get("est_cost_usd")
        })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(predicted_set, f, ensure_ascii=False, indent=4)


test_agent_predictions()