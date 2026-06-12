# SoukAI

SoukAI is an Arabic e-commerce customer support triage agent built for the **SoukAI GenAI engineering challenge**. The goal is to triage Arabic customer messages for a hypothetical pan-Arab marketplace and help CX teams decide what should be auto-handled, routed, or escalated.

The project focuses on practical Arabic-language support scenarios across **Modern Standard Arabic (MSA)** and regional dialects including **Egyptian, Gulf, Levantine, and Maghrebi**.

## Overview

SoukAI receives large volumes of customer messages through its app and website: delivery complaints, refund requests, app bugs, billing issues, product quality problems, positive feedback, and abusive or spam content. SoukAI is designed as the AI triage layer in front of human support operations.

For each incoming Arabic message, the target workflow is to:

- classify the message into a known support intent
- assess urgency as `high`, `medium`, or `low`
- extract entities such as order IDs, dates, amounts, and contact details
- retrieve supporting context from a mock orders database and a mock Arabic knowledge base
- decide whether to auto-respond, route to a team, or escalate to a human
- draft an Arabic response in a suitable register


## Dataset

This project uses the **HARD (Hotel Arabic Reviews Dataset)** as the primary dataset source:

- GitHub: `https://github.com/elnagara/HARD-Arabic-Dataset`

Why this dataset was used:

- it provides substantial Arabic review text
- it includes varied sentiment signals useful for customer-experience analysis
- it helps stress-test Arabic text handling across different writing styles

Important limitation:

- HARD is a **hotel reviews** dataset, not a native e-commerce customer support dataset

Because of that, the dataset is used here as a **foundation for Arabic language understanding and evaluation**, while the triage problem itself is adapted to the SoukAI e-commerce scenario with mock support data, intent logic, and evaluation assets.

## High-Level System Design

At a high level, SoukAI is structured around these stages:

1. **Input validation and normalization**
2. **Safety filtering**
3. **Intent classification**
4. **Entity extraction**
5. **Oredr retrieval from mock order data**
5. **KB retrieval from mock Arabic Knowledge Base**
6. **Routing or escalation decision**
7. **Arabic response generation**
8. **Evaluation and reporting**


## Project Structure

```text
SoukAI/
├── README.md
├── requirements.txt
├── data/
│   ├── dataset.csv
│   ├── raw/
│   ├── mock/
│   │   ├── orders_database.json
│   │   └── arabic_knowledge_base.json
│   └── test/
├── evaluation/
│   ├── Classification/
│   ├── LLM_as_judge/
│   └── test_agent.py
└── src/
    ├── main.py
    ├── helpers/
    ├── prompts/
    ├── routes/
    ├── stores/
    |   └── providers/
    └── tools/
```

## 🛠️ Initial Setup

### 1. Clone the project

```bash
git clone https://github.com/Abdelrhman-T/SoukAI.git
```

### 2. Navigate to project
```bash
cd SoukAI
```

### 3. Create Python environment

```bash
python -m venv .soukai
```

Windows (Command Prompt):
```bash
.soukai\Scripts\activate.bat
```

Windows (PowerShell):
```bash
.soukai\Scripts\activate.bat
```

Or use Conda

```bash
conda create -n soukai python=3.14.3
conda activate soukai
```

### 4. Installing dependencies

```bash
cd SoukAI/src/
pip install -r requirements.txt
```
---

### 5. Configure environment files

```bash
cd SoukAI/src/env
cp .env.example.app .env
```
- Add your api_keys
- Choose your preferred Provider
- Choose your preferred Model

---

### 6. Start api endpoints

```bash
cd SoukAI/src
uvicorn main:app --reload
```

- You can use FastAPI Docs by `http://localhost:8000/docs` and use `/api/v1/agent/answer`
- You can use Postman or Apidog by configer `http://localhost/api/v1/agent/answer`

---

### 7. Enjoy by send messages


---

## 🌍 Service Endpoints

| Service           | URL                                                                                   |
| ------------------| --------------------------------------------------------------------------------------|
| FastAPI           | [http://localhost:8000](http://localhost:8000)                                        |
| API Docs          | [http://localhost:8000/docs](http://localhost:8000/docs)                              |
| Test Server       | [http://localhost:8000/api/v1/](http://localhost:8000/api/v1/)                        |
| Test LLM Provider | [http://localhost:8000/api/v1/nlp/answer](http://localhost:8000/api/v1/nlp/answer)    |
| Use Agent Flow    | [http://localhost:8000/api/v1/agent/answer](http://localhost:8000/api/v1/agent/answer)|

---

## Additional Documentation

* `evaluation\README.md` → Evaluation Report

---

##  Notes

* Ensure consistency between environment files to avoid connection issues

---

## 👤 Author

* **Name:** Eng. Abdelrhman Tarek
* **Role:** AI/ML Engineer
* **LinkedIn:** [https://www.linkedin.com/in/abdelrhman-tarek-mohamed/](https://www.linkedin.com/in/abdelrhman-tarek-mohamed/)
* **Portfolio:** [https://abdelrhman-t.github.io/](https://abdelrhman-t.github.io/)
* **GitHub:** [https://github.com/Abdelrhman-T](https://github.com/Abdelrhman-T)


## Summary

SoukAI is a baseline Arabic customer support triage agent for a pan-Arab e-commerce setting. It combines Arabic preprocessing, intent classification, mock retrieval, safety checks, and LLM response generation, with evaluation artifacts included to support end-to-end reasoning about quality and tradeoffs.
