import json
import re
from pathlib import Path

from tools.arabic_utils import normalize_arabic

ORDER_RE = re.compile(
    r"ORD[-_]?(\d{4,10})|(?:رقم\s*الطلب|كود\s*الطلب|الطلب|الرقم)\s*[:#-]?\s*(\d{4,10})",
    re.IGNORECASE,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "mock"
ORDERS_DB_PATH = DATA_DIR / "orders_database.json"
KB_DB_PATH = DATA_DIR / "arabic_knowledge_base.json"


def extract_order_id(text: str):
    if not text:
        return None

    match = ORDER_RE.search(text)

    if not match:
        return None

    return next(g for g in match.groups() if g)


def lookup_order(order_id):
    if not order_id:
        return None

    with ORDERS_DB_PATH.open("r", encoding="utf-8") as file:
        orders = json.load(file)

    if not isinstance(orders, list):
        return None

    for order in orders:
        if not isinstance(order, dict):
            continue

        candidate_id = order.get("order_id")
        if str(candidate_id) == str(order_id):
            return order

    return None


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def search_kb(query, intent):
    if not query or not intent:
        return []

    norm_query = normalize_arabic(query)

    knowledge_base = _load_json(KB_DB_PATH)

    if not isinstance(knowledge_base, list):
        return []

    matches = []
    for item in knowledge_base:
        if not isinstance(item, dict):
            continue

        applies_to_intents = item.get("applies_to_intents", [])
        if isinstance(applies_to_intents, list) and intent in applies_to_intents:
            matches.append(item)

    return matches
