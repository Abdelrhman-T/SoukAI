# Evaluation Report

This folder contains the evaluation artifacts for the SoukAI review-classification and response-generation pipeline.

## Artifacts Used

- `evaluation/test_dataset.json`: labeled test set
- `evaluation/Classification/evaluation_report.json`: classification metrics
- `evaluation/LLM_as_judge/response_judgments_with_context.json`: per-example qualitative judgments
- `evaluation/LLM_as_judge/response_judgment_summary.json`: qualitative metric summary
- `evaluation/predicted_set.json`: model predictions, generated responses, latency, and estimated cost

### Note:
- `test_dataset` labeled by Claude not Hand-labeled
- `predicted_set` labeled by SoukAI agent


## 1. Labeled Test Set

The labeled evaluation set contains `71` examples. Each row has:

- `review`
- `intent`
- `urgency`
- `requires_human`
- `routed_team`

### Label Distribution

#### Intent

| Intent | Count |
| --- | ---: |
| `delivery_issue` | 2 |
| `other` | 11 |
| `payment_issue` | 1 |
| `positive_feedback` | 26 |
| `product_quality` | 29 |
| `refund_request` | 2 |

#### Urgency

| Urgency | Count |
| --- | ---: |
| `high` | 36 |
| `low` | 35 |

#### Requires Human

| Requires Human | Count |
| --- | ---: |
| `true` | 39 |
| `false` | 32 |

#### Routed Team

| Routed Team | Count |
| --- | ---: |
| `Auto Response` | 33 |
| `Billing` | 1 |
| `CX Manager` | 33 |
| `Logistics` | 2 |
| `Returns` | 2 |

## 2. Intent Classification Metrics

Source: `evaluation/Classification/evaluation_report.json`

Overall intent accuracy: `0.5915`

| Intent | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `delivery_issue` | 1.0000 | 0.5000 | 0.6667 | 2 |
| `other` | 0.8571 | 0.5455 | 0.6667 | 11 |
| `payment_issue` | 0.3333 | 1.0000 | 0.5000 | 1 |
| `positive_feedback` | 0.8750 | 0.2692 | 0.4118 | 26 |
| `product_quality` | 0.5417 | 0.8966 | 0.6753 | 29 |
| `refund_request` | 0.2500 | 0.5000 | 0.3333 | 2 |
| `weighted_avg` | 0.7144 | 0.5916 | 0.5651 | 71 |

## 3. Routing Accuracy

Source: `evaluation/Classification/evaluation_report.json`

| Field | Accuracy |
| --- | ---: |
| `routed_team` | 0.5775 |
| `urgency` | 0.4225 |
| `requires_human` | 0.6479 |

## 4. Qualitative Response Quality

Sources:

- I used chatgpt as judge using prompt in `src\prompts\judge_prompt.py`
- `evaluation/LLM_as_judge/response_judgments_with_context.json`
- `evaluation/LLM_as_judge/response_judgment_summary.json`



### Metric Definition

Response quality was evaluated with an LLM-as-judge rubric. For each generated response, the judge assigns:

- `correctness` on a 1-5 scale
- `helpfulness` on a 1-5 scale
- `dialect_match` on a 1-5 scale
- `tone` on a 1-5 scale
- `overall_score`
- `pass`
- `failure_category`
- `short_reason`

This is a justified qualitative metric because there is no single gold response for each review. A rubric-based judge is appropriate here because the task quality depends on multiple business-relevant dimensions beyond classification alone: factual correctness, usefulness to the customer, matching the user's dialect, and maintaining an appropriate support tone.

### Results

| Metric | Value |
| --- | ---: |
| Total judged cases | 71 |
| Passed | 52 |
| Failed | 19 |
| Pass rate | 73.24% |
| Average overall score | 4.08 / 5 |
| Average correctness | 4.08 / 5 |
| Average helpfulness | 3.69 / 5 |
| Average dialect match | 3.83 / 5 |
| Average tone | 4.72 / 5 |

## 5. Average Cost and Latency Per Message

Source: `evaluation/predicted_set.json`

| Metric | Value |
| --- | ---: |
| Messages evaluated | 71 |
| Average latency | 4578.91 ms |
| Average latency | 4.58 s |
| Min latency | 5.29 ms |
| Max latency | 8144.34 ms |
| Average estimated cost | 0.0 USD |
| Total estimated cost | 0.0 USD |

- The Cost here = 0 because i used free provider (groq)
- You can change it to OpenRouter by just .env file

## 6. Breakdown of Failures by Category

### A. Classification Failure Patterns

Largest intent confusions from the confusion matrix:

| True Intent | Predicted Intent | Count |
| --- | --- | ---: |
| `positive_feedback` | `product_quality` | 18 |
| `other` | `product_quality` | 3 |
| `product_quality` | `refund_request` | 2 |
| `delivery_issue` | `product_quality` | 1 |
| `other` | `positive_feedback` | 1 |
| `other` | `refund_request` | 1 |
| `product_quality` | `other` | 1 |
| `refund_request` | `payment_issue` | 1 |


Main pattern: the model over-predicts `product_quality`, especially for reviews that are actually `positive_feedback` or `other`.
- we can handle it by update `src\helpers\intent_rules.py`

### B. Response Quality Failure Categories

Source: `evaluation/LLM_as_judge/response_judgment_summary.json`

| Failure Category | Count |
| --- | ---: |
| `generic_response` | 8 |
| `wrong_dialect` | 4 |
| `incorrect_answer` | 3 |
| `unsupported_promise` | 3 |
| `missed_escalation` | 1 |

Notes:

- `generic_response` is the biggest response-quality failure mode.
- `wrong_dialect` shows the model often answers in acceptable Arabic, but not always in the dialect implied by the review.
- `unsupported_promise` means the response commits to actions such as refunds or timelines too strongly.
- `missed_escalation` is low in count, but high in operational risk.

- we can handle it by update `src\prompts\system_prompt.py`

## Summary

The system is strongest on:

- `product_quality` recall
- response tone
- human-escalation detection relative to the other routing fields

The system is weakest on:

- separating `positive_feedback` from `product_quality`
- `urgency` prediction
- avoiding generic responses
- matching dialect consistently in generated replies
