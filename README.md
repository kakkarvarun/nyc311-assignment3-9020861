# NYC 311 Service Requests – Data-Driven Web App

![CI](https://github.com/kakkarvarun/nyc311-assignment3-9020861/actions/workflows/ci.yml/badge.svg)

Flask + MySQL web app that ingests a one-month slice of the **NYC 311 Service Requests** dataset, exposes a **search UI** (date range, borough, complaint filter) with **pagination**, and an **aggregate view** (“Complaints per Borough”). Includes a **chunked ETL** pipeline with cleaning + idempotency, **Selenium tests**, and **GitHub Actions CI**. No secrets in code — DB credentials are provided via environment variables and GitHub Secrets/Variables.

---

## Architecture (high-level)
1. **ETL (Python/Pandas)** → chunked CSV → cleaned rows → MySQL (`service_requests`)  
2. **MySQL schema** → PK + **two indexes** for filters; `ingestion_log` for idempotency & metrics  
3. **Flask app** → search with pagination; aggregate; templates in `app/templates`  
4. **Tests** → Selenium positive/negative/aggregate (headless in CI)  
5. **CI/CD** → Start MySQL, load schema, run ETL on a tiny fixture, start Flask, run tests

---

## Dataset
- Source: [NYC 311 – Open Data NYC](https://data.cityofnewyork.us/Social-Services/erm2-nwe9)
- **Use one month** (e.g., `2023-01`) to keep local runs fast.
- Place CSV locally at `data/311_YYYY_MM.csv` (git-ignored).

---

## Quickstart (Local – Docker)
```bash
# 1) Create .env from example (do NOT commit your real secrets)
cp .env.example .env
# Set strong APP_DB_PASSWORD and MYSQL_ROOT_PASSWORD in .env

# 2) Start services and build images
docker compose up -d --build

# 3) Load one-month CSV via the bind mount path
#    (example: January 2023)
docker compose exec web python etl/etl.py --file /app/data/311_2023_01.csv --month 2023-01

# 4) App is available at:
#    http://localhost:5000

Search UI: filter by date range, borough, and complaint substring.
Aggregate: /aggregate/borough for complaints per borough.

Schema & Indexes

Tables:

service_requests (PK: request_id, created_datetime, borough, complaint_type, etc.)

ingestion_log (idempotent month key, status, row_count, JSON details)

Indexes (chosen to match filters/pagination):

idx_created_datetime (created_datetime)

idx_borough_type_date (borough, complaint_type, created_datetime)

EXPLAIN confirms index usage for the search query:

EXPLAIN
SELECT request_id
FROM service_requests
WHERE borough='BROOKLYN'
  AND complaint_type LIKE '%Noise%'
  AND created_datetime BETWEEN '2023-01-01' AND '2023-01-31'
ORDER BY created_datetime DESC
LIMIT 20;


ETL

Reads CSV in chunks (default 50k rows), inserts in batches (10k) with transactions.

Cleans/normalizes: parse timestamps, fill missing borough as UNKNOWN, drop invalid dates.

Idempotent by month: deletes existing month before inserting; records metrics in ingestion_log with JSON details.

Telemetry printed per chunk: rows/s, CPU%, Mem%.

Run:

docker compose exec web python etl/etl.py \
  --file /app/data/311_2023_01.csv \
  --month 2023-01 \
  --chunksize 50000 \
  --batch 10000

Tests

Selenium tests run locally and in CI (headless Chrome):

pytest -q
test_positive_search → has results for BROOKLYN + “Noise” in Jan 2023

test_negative_search → no results for a deliberately impossible combo

test_aggregate → aggregate page loads

CI (GitHub Actions)

Workflow: .github/workflows/ci.yml

Starts MySQL 8 via docker run

Loads schema; creates least-privileged app user

Runs ETL on tiny fixture: tests/fixtures/311_sample.csv

Starts Flask app; runs headless Selenium tests

Secrets/Variables required (Repo → Settings → Secrets and variables → Actions):

Secrets: MYSQL_ROOT_PASSWORD, APP_DB_PASSWORD

Variables: APP_DB_USER=appuser, DB_NAME=nyc311, DB_HOST=127.0.0.1, DB_PORT=3306

Security

No credentials in code or logs.

Local: .env (git-ignored).

CI: use GitHub Secrets and Variables.