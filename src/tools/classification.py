from nltk.stem.isri import ISRIStemmer

from helpers import intent_rules
from tools.arabic_utils import ratio_hits, tokenize

_isri_stemmer = ISRIStemmer()

def classify_intent(text: str):

    best_intent = intent_rules.DEFAULT_INTENT
    best_score = 0.0

    tokens = tokenize(text)

    stem_tokens = [_isri_stemmer.stem(token) for token in tokens]

    if not text or not stem_tokens:
        return intent_rules.DEFAULT_INTENT,best_score
    
    scores = []

    for intent, rules in intent_rules.INTENT_RULES.items():
        stem_rule = [_isri_stemmer.stem(rule) for rule in rules]
        ratio = ratio_hits(stem_tokens, stem_rule)

        scores.append(ratio)
        if ratio > best_score:
            best_intent = intent
            best_score = ratio

    confidence = (best_score/ sum(scores))*100 

    return best_intent, round(confidence, 1)