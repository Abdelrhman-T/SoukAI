# ArabCX

ArabCX is an Arabic e-commerce customer support triage agent built for the **ArabCX GenAI engineering challenge**. The goal is to triage Arabic customer messages for a hypothetical pan-Arab marketplace and help CX teams decide what should be auto-handled, routed, or escalated.

The project focuses on practical Arabic-language support scenarios across **Modern Standard Arabic (MSA)** and regional dialects including **Egyptian, Gulf, Levantine, and Maghrebi**.

## Overview

ArabCX receives large volumes of customer messages through its app and website: delivery complaints, refund requests, app bugs, billing issues, product quality problems, positive feedback, and abusive or spam content. ArabCX is designed as the AI triage layer in front of human support operations.

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

Because of that, the dataset is used here as a **foundation for Arabic language understanding and evaluation**, while the triage problem itself is adapted to the ArabCX e-commerce scenario with mock support data, intent logic, and evaluation assets.

## High-Level System Design

At a high level, ArabCX is structured around these stages:

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
ArabCX/
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
git clone https://github.com/Abdelrhman-T/ArabCX.git
```

### 2. Navigate to project
```bash
cd ArabCX
```

### 3. Create Python environment

```bash
python -m venv .arabcx
```

Windows (Command Prompt):
```bash
.arabcx\Scripts\activate.bat
```

Windows (PowerShell):
```bash
.arabcx\Scripts\activate.bat
```

Or use Conda

```bash
conda create -n arabcx python=3.14.3
conda activate arabcx
```

### 4. Installing dependencies

```bash
cd ArabCX/
pip install -r requirements.txt
```
---

### 5. Configure environment files

```bash
cd ArabCX/src/env
cp .env.example .env
```
- Add your api_keys
- Choose your preferred Provider
- Choose your preferred Model

---

### 6. Start api endpoints

```bash
cd ArabCX/src
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


## Facebook Page Integration

ArabCX can be connected to a Facebook Page webhook to receive new page comments, process them through the agent flow, and reply automatically.

### 1. Configure Facebook environment variables

Add the following values to your `.env` file:

```env
FACEBOOK_PAGE_ACCESS_TOKEN=your_page_access_token
FACEBOOK_PAGE_ID=your_facebook_page_id
META_VERIFY_TOKEN=arabcx_verify_123
```

Notes:

* `FACEBOOK_PAGE_ACCESS_TOKEN` must be a valid Page Access Token.
* `FACEBOOK_PAGE_ID` is the ID of the Facebook Page you want to connect.
* `META_VERIFY_TOKEN` must match the token you enter in Meta Webhooks.

---

### 2. Run the FastAPI server

From the `src` directory, run:

```bash
cd ArabCX/src
uvicorn main:app --reload
```

The API should now be available at:

```text
http://localhost:8000
```

You can also open the FastAPI documentation from:

```text
http://localhost:8000/docs
```

---

### 3. Expose the local server using ngrok

Open a second terminal and run:

```bash
C:\ngrok\ngrok.exe http 8000
```

ngrok will generate a public HTTPS URL similar to:

```text
https://f531-197-133-80-228.ngrok-free.app
```

Keep this terminal running while testing the Facebook integration.

Important: if you restart ngrok, the public URL may change. In that case, update the Callback URL in Meta Developer Dashboard.

---

### 4. Configure Meta Webhooks

Go to:

```text
Meta Developer Dashboard
→ Your App
→ Webhooks
→ Page
```

Set the webhook configuration as follows:

```text
Callback URL:
https://YOUR_NGROK_URL.ngrok-free.app/api/v1/meta/webhook

Verify Token:
arabcx_verify_123
```

Example:

```text
Callback URL:
https://f531-197-133-80-228.ngrok-free.app/api/v1/meta/webhook

Verify Token:
arabcx_verify_123
```

Then subscribe to the Page webhook field:

```text
feed
```

This allows ArabCX to receive new Facebook Page comment events.

---

### 5. Subscribe the Facebook Page to the App

Using Graph API Explorer with a valid Page Access Token, subscribe the page to the app:

```http
POST /{PAGE_ID}/subscribed_apps
```

With parameter:

```text
subscribed_fields=feed
```

You can verify the subscription with:

```http
GET /{PAGE_ID}/subscribed_apps?fields=name,subscribed_fields
```

Expected result should include:

```json
{
  "name": "ArabCX",
  "subscribed_fields": [
    "feed"
  ]
}
```

---

### 6. Test the webhook

First, test from Meta Developer Dashboard:

```text
Webhooks
→ Page
→ feed
→ Test
```

You should see the request appear in:

```text
ngrok inspector: http://127.0.0.1:4040
```

and in the FastAPI terminal.

---

### 7. Test with a real Facebook comment

Create or open a normal post on your Facebook Page, then add a new comment from a personal Facebook account.

Example comment:

```text
الاوردر متأخر ومحدش بيرد عليا رقم الطلب 12345
```

If the integration is configured correctly, ArabCX will receive the comment, process it through the agent, and reply automatically on the Facebook comment.


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

ArabCX is a baseline Arabic customer support triage agent for a pan-Arab e-commerce setting. It combines Arabic preprocessing, intent classification, mock retrieval, safety checks, and LLM response generation, with evaluation artifacts included to support end-to-end reasoning about quality and tradeoffs.
