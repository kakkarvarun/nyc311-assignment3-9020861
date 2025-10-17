# Assignment 3 – NYC 311 Service Requests App

This is the starter repository for Assignment 3.

## Getting Started
1. Copy `.env.example` → `.env`.
2. Run `docker compose up -d --build`.
3. Load data into MySQL using `etl/etl.py`.
4. Run Flask app at http://localhost:5000.

## To Do
- Implement ETL script with chunked loading.
- Extend Flask app with search filters + aggregate view.
- Write Selenium tests.
- Configure GitHub Actions workflow.
