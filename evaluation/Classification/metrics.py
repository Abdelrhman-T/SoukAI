from typing import Any, Dict, List


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def classification_report_per_class(
    y_true: List[str],
    y_pred: List[str],
) -> Dict[str, Dict[str, float]]:
    

    labels = sorted(set(y_true) | set(y_pred))

    report: Dict[str, Dict[str, float]] = {}

    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)

        precision = safe_divide(tp, tp + fp)
        recall = safe_divide(tp, tp + fn)
        f1 = safe_divide(2 * precision * recall, precision + recall)
        support = sum(1 for t in y_true if t == label)

        report[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }

    return report


def accuracy_score(
    y_true: List[Any],
    y_pred: List[Any],
) -> float:

    if len(y_true) == 0:
        return 0.0

    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return round(correct / len(y_true), 4)



def weighted_average(
    report: Dict[str, Dict[str, float]],
) -> Dict[str, float]:

    total_support = sum(v["support"] for v in report.values())

    if total_support == 0:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
        }

    precision = sum(v["precision"] * v["support"] for v in report.values()) / total_support
    recall = sum(v["recall"] * v["support"] for v in report.values()) / total_support
    f1 = sum(v["f1"] * v["support"] for v in report.values()) / total_support

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def confusion_matrix_as_dict(
    y_true: List[str],
    y_pred: List[str],
) -> Dict[str, Dict[str, int]]:

    labels = sorted(set(y_true) | set(y_pred))
    matrix = {true_label: {pred_label: 0 for pred_label in labels} for true_label in labels}

    for true_label, pred_label in zip(y_true, y_pred):
        matrix[true_label][pred_label] += 1

    return matrix