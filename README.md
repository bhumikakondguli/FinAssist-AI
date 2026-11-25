# FinAssist AI — Personal Finance Management and Analysis

A runnable academic prototype for transaction tracking, budgets, CSV import/export, charts, monthly reports and a conversational finance assistant. Backend totals are calculated deterministically; optional LLM integration explains supplied summaries. The fallback assistant works without an API key.

## Features
- Dashboard with monthly income, expenses and balance
- Add and delete income/expense transactions
- Rule-based category suggestion (category can be selected manually)
- Monthly/category budget limits and utilization bars
- CSV import and export
- Spending chart (Chart.js)
- Monthly report
- FinAssist chat: rule-based fallback or optional OpenAI API integration
- SQLite database created automatically

## Run (Windows)
1. Install Python 3.10+.
2. Extract this ZIP and open a terminal in the `finassist_ai` folder.
3. Create a virtual environment:
   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   ```
4. Install dependencies:
   ```bat
   pip install -r requirements.txt
   ```
5. Optional: copy `.env.example` to `.env` and set `OPENAI_API_KEY` to enable API-backed explanations. Keep this key private; never commit `.env`.
6. Start the app:
   ```bat
   python app.py
   ```
7. Open http://127.0.0.1:5000 in your browser.

## Run (macOS/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Optional: cp .env.example .env and set the API key
python app.py
```

## CSV import format
CSV headers are `date,description,amount,type,category` (category is optional). Dates must be ISO format `YYYY-MM-DD`, type must be `income` or `expense`, and amounts must be positive.
A sample file is included as `sample_transactions.csv`.

## Notes and limitations
- Prototype uses a local SQLite database and has no authentication or bank integration. Treat data as demonstration data and avoid entering sensitive real financial records.
- This application is for budgeting awareness, not professional financial, tax, credit or investment advice.
- The optional OpenAI integration requires the `openai` package and a valid API key. Without it, supported questions receive a transparent rule-based response.
- Charts use CDN-hosted Chart.js and Bootstrap; internet access is required for those assets.
- Only perform tests and report results that you have actually run.
