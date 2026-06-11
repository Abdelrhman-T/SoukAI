import json
from pathlib import Path
from typing import Any, Dict, List

from metrics import (accuracy_score, classification_report_per_class,
                     confusion_matrix_as_dict, weighted_average)

REAL_PATH = Path("../test_dataset.json")
PRED_PATH = Path("../predicted_set.json")
OUTPUT_PATH = Path("evaluation_report.json")


FIELDS_TO_COMPARE = [
    "intent",
    "urgency",
    "requires_human",
    "routed_team",
]


def load_json(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list.")

    return data


def validate_lengths(real_data: List[Dict[str, Any]], pred_data: List[Dict[str, Any]]) -> None:
    if len(real_data) != len(pred_data):
        raise ValueError(
            f"Length mismatch: real={len(real_data)}, predicted={len(pred_data)}"
        )


def validate_required_fields(
    real_data: List[Dict[str, Any]],
    pred_data: List[Dict[str, Any]],
) -> None:
    for i, (real_item, pred_item) in enumerate(zip(real_data, pred_data)):
        for field in FIELDS_TO_COMPARE:
            if field not in real_item:
                raise KeyError(f"Missing field `{field}` in real data at index {i}")

            if field not in pred_item:
                raise KeyError(f"Missing field `{field}` in predicted data at index {i}")


def extract_field_values(
    real_data: List[Dict[str, Any]],
    pred_data: List[Dict[str, Any]],
    field: str,
) -> tuple[List[Any], List[Any]]:
    y_true = [item[field] for item in real_data]
    y_pred = [item[field] for item in pred_data]

    return y_true, y_pred


def evaluate(real_data: List[Dict[str, Any]], pred_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    validate_lengths(real_data, pred_data)
    validate_required_fields(real_data, pred_data)

    total_samples = len(real_data)

    # Intent classification metrics
    intent_true, intent_pred = extract_field_values(real_data, pred_data, "intent")

    intent_report = classification_report_per_class(
        y_true=intent_true,
        y_pred=intent_pred,
    )

    # Accuracy for other fields
    urgency_true, urgency_pred = extract_field_values(real_data, pred_data, "urgency")
    human_true, human_pred = extract_field_values(real_data, pred_data, "requires_human")
    team_true, team_pred = extract_field_values(real_data, pred_data, "routed_team")

    results = {
        "total_samples": total_samples,

        "intent": {
            "accuracy": accuracy_score(intent_true, intent_pred),
            "per_class": intent_report,
            "weighted_avg": weighted_average(intent_report),
            "confusion_matrix": confusion_matrix_as_dict(intent_true, intent_pred),
        },

        "urgency": {
            "accuracy": accuracy_score(urgency_true, urgency_pred),
        },

        "requires_human": {
            "accuracy": accuracy_score(human_true, human_pred),
        },

        "routed_team": {
            "accuracy": accuracy_score(team_true, team_pred),
        },
    }

    return results


def print_summary(report: Dict[str, Any]) -> None:
    print("=" * 60)
    print("Evaluation Summary")
    print("=" * 60)

    print(f"Total samples: {report['total_samples']}")
    print()

    print("Intent Metrics")
    print("-" * 60)
    print(f"Intent accuracy: {report['intent']['accuracy']}")
    print(f"Weighted F1:     {report['intent']['weighted_avg']['f1']}")
    print()

    print("Intent Per-Class Report")
    print("-" * 60)

    for label, scores in report["intent"]["per_class"].items():
        print(
            f"{label:25s} "
            f"P: {scores['precision']:.4f} "
            f"R: {scores['recall']:.4f} "
            f"F1: {scores['f1']:.4f} "
            f"Support: {scores['support']}"
        )

    print()
    print("Other Accuracy Metrics")
    print("-" * 60)
    print(f"Urgency accuracy:        {report['urgency']['accuracy']}")
    print(f"Requires human accuracy: {report['requires_human']['accuracy']}")
    print(f"Routed team accuracy:    {report['routed_team']['accuracy']}")


def save_report(report: Dict[str, Any], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=4)


def main() -> None:
    real_data = load_json(REAL_PATH)
    pred_data = load_json(PRED_PATH)

    report = evaluate(real_data, pred_data)

    print_summary(report)
    save_report(report, OUTPUT_PATH)

    print()
    print(f"Saved full report to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()