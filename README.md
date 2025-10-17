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

# NYC 311 Service Requests App

Flask + MySQL app to explore a single-month slice of NYC 311 with chunked ETL, indexes, pagination, aggregate view, Selenium tests, and GitHub Actions CI.

## Local (Docker)
```bash
cp .env.example .env     # set strong values for APP_DB_PASSWORD and MYSQL_ROOT_PASSWORD
docker compose up -d --build

# ETL (load your month CSV, e.g., Jan 2023)
docker compose cp data/311_2023_01.csv web:/app/data/311_2023_01.csv
docker compose exec web python etl/etl.py --file data/311_2023_01.csv --month 2023-01

# App at http://localhost:5000
Filters & Aggregates

Search by date range, borough, complaint contains, with pagination

Aggregate: Complaints per Borough

Schema & Indexes

Tables: service_requests, ingestion_log

Indexes:

idx_created_datetime (created_datetime)

idx_borough_type_date (borough, complaint_type, created_datetime)

ETL

Chunked ingest (default 50k), batch insert (10k), idempotent per month_key

Telemetry prints rows/s, CPU%, Mem%, chunk-by-chunk

Tests

pytest -q

CI

MySQL service + schema + least-privileged user from GitHub Secrets/Variables

ETL on a tiny fixture; headless Selenium

No secrets in code or logs

Performance sample (replace with actual)
Chunk	Batch	Rows	Duration (s)	Rows/s	CPU%	Mem%
50,000	10,000	300,000	80	3,750	40	35