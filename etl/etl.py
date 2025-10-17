import os, sys, time
import pandas as pd
import pymysql
from dotenv import load_dotenv
import psutil
import argparse
import json


USECOLS = [
    "Unique Key","Created Date","Closed Date","Agency","Agency Name",
    "Complaint Type","Descriptor","Borough","City",
    "Latitude","Longitude","Status","Resolution Description"
]

DTYPES = {
    "Unique Key": "Int64",
    "Agency": "string",
    "Agency Name": "string",
    "Complaint Type": "string",
    "Descriptor": "string",
    "Borough": "string",
    "City": "string",
    "Latitude": "float64",
    "Longitude": "float64",
    "Status": "string",
    "Resolution Description": "string",
}
DATE_COLS = ["Created Date","Closed Date"]

def _req(name): 
    v = os.getenv(name)
    if not v: raise RuntimeError(f"Missing env var: {name}")
    return v

def connect():
    load_dotenv()
    return pymysql.connect(
        host=_req("DB_HOST"),
        port=int(os.getenv("DB_PORT","3306")),
        user=_req("DB_USER"),
        password=_req("DB_PASSWORD"),
        database=_req("DB_NAME"),
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4"
    )

def args_parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--chunksize", type=int, default=50000)
    ap.add_argument("--batch", type=int, default=10000)
    ap.add_argument("--limit", type=int, default=0)
    return ap.parse_args()

def start_log(conn, month_key, source_file):
    sql = """INSERT INTO ingestion_log (month_key, source_file, started_at, status)
             VALUES (%s,%s,NOW(),'started')
             ON DUPLICATE KEY UPDATE started_at=VALUES(started_at), status='started', details=NULL"""
    with conn.cursor() as cur: cur.execute(sql, (month_key, source_file))
    conn.commit()

def finish_log(conn, month_key, rows, status, details=None):
    sql = "UPDATE ingestion_log SET finished_at=NOW(), row_count=%s, status=%s, details=%s WHERE month_key=%s"

    # Ensure the JSON column gets valid JSON
    if details is None:
        payload = None  # store NULL
    elif isinstance(details, str):
        # If you pass in a string, try to make it valid JSON string; otherwise wrap it
        try:
            json.loads(details)  # is it already JSON?
            payload = details
        except json.JSONDecodeError:
            payload = json.dumps({"message": details})
    else:
        # dict or list → proper JSON
        payload = json.dumps(details)

    with conn.cursor() as cur:
        cur.execute(sql, (rows, status, payload, month_key))
    conn.commit()


def delete_month(conn, month_key):
    with conn.cursor() as cur: cur.execute("DELETE FROM service_requests WHERE month_key=%s", (month_key,))
    conn.commit()

def clean_chunk(df):
    df = df[USECOLS].copy()
    for c,t in DTYPES.items():
        if c in df: df[c] = df[c].astype(t)
    for c in DATE_COLS:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df = df[(df["Created Date"].notna()) & (df["Created Date"] >= "2010-01-01")]
    df["Borough"] = df["Borough"].fillna("UNKNOWN").replace({"": "UNKNOWN", "Unspecified":"UNKNOWN"})
    df["Complaint Type"] = df["Complaint Type"].fillna("UNKNOWN")
    df["month_key"] = df["Created Date"].dt.strftime("%Y-%m")
    out = pd.DataFrame({
        "request_id": df["Unique Key"].astype("Int64"),
        "created_datetime": df["Created Date"],
        "closed_datetime": df["Closed Date"],
        "agency": df["Agency"],
        "agency_name": df["Agency Name"],
        "complaint_type": df["Complaint Type"],
        "descriptor": df["Descriptor"],
        "borough": df["Borough"],
        "city": df["City"],
        "latitude": df["Latitude"],
        "longitude": df["Longitude"],
        "status": df["Status"],
        "resolution_description": df["Resolution Description"],
        "month_key": df["month_key"]
    })
    out = out[out["request_id"].notna()]
    return out

def insert_batch(conn, rows):
    sql = """
    INSERT INTO service_requests
    (request_id, created_datetime, closed_datetime, agency, agency_name, complaint_type, descriptor,
     borough, city, latitude, longitude, status, resolution_description, month_key)
    VALUES
    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON DUPLICATE KEY UPDATE
      created_datetime=VALUES(created_datetime),
      closed_datetime=VALUES(closed_datetime),
      agency=VALUES(agency),
      agency_name=VALUES(agency_name),
      complaint_type=VALUES(complaint_type),
      descriptor=VALUES(descriptor),
      borough=VALUES(borough),
      city=VALUES(city),
      latitude=VALUES(latitude),
      longitude=VALUES(longitude),
      status=VALUES(status),
      resolution_description=VALUES(resolution_description),
      month_key=VALUES(month_key)
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)

def main():
    args = args_parse()
    total = 0
    t0 = time.time()
    conn = connect()
    try:
        start_log(conn, args.month, os.path.basename(args.file))
        delete_month(conn, args.month)

        chunks = pd.read_csv(
            args.file, usecols=USECOLS, dtype=DTYPES,
            parse_dates=DATE_COLS, chunksize=args.chunksize, low_memory=False
        )

        remaining = args.limit if args.limit > 0 else None
        for i, chunk in enumerate(chunks, 1):
            df = clean_chunk(chunk)
            if remaining is not None:
                if len(df) > remaining: df = df.iloc[:remaining]
                remaining -= len(df)

            tuples = []
            for r in df.itertuples(index=False):
                # Convert datetimes safely (NaT -> None)
                created_dt = r.created_datetime.to_pydatetime() if pd.notna(r.created_datetime) else None
                closed_dt  = r.closed_datetime.to_pydatetime() if pd.notna(r.closed_datetime) else None

                tuples.append((
                    int(r.request_id),
                    created_dt,
                    closed_dt,
                    (r.agency if pd.notna(r.agency) else None),
                    (r.agency_name if pd.notna(r.agency_name) else None),
                    (r.complaint_type if pd.notna(r.complaint_type) else "UNKNOWN"),
                    (r.descriptor if pd.notna(r.descriptor) else None),
                    (r.borough if pd.notna(r.borough) else "UNKNOWN"),
                    (r.city if pd.notna(r.city) else None),
                    (float(r.latitude) if not pd.isna(r.latitude) else None),
                    (float(r.longitude) if not pd.isna(r.longitude) else None),
                    (r.status if pd.notna(r.status) else None),
                    (r.resolution_description if pd.notna(r.resolution_description) else None),
                    r.month_key
            ))


            for j in range(0, len(tuples), args.batch):
                batch = tuples[j:j+args.batch]
                try:
                    insert_batch(conn, batch)
                    conn.commit()
                    total += len(batch)
                except Exception:
                    conn.rollback()
                    raise

            elapsed = time.time() - t0
            rps = total/elapsed if elapsed else 0
            print(f"[chunk {i}] inserted={total} rows  rps={rps:,.0f}  cpu={psutil.cpu_percent()}%  mem={psutil.virtual_memory().percent}%")
            if remaining is not None and remaining <= 0:
                break

        finish_log(conn, args.month, total, "success", {
            "duration_sec": round(time.time() - t0, 2),
            "chunksize": args.chunksize,
            "batch": args.batch,
            "inserted": total
        })

        print(f"[done] rows={total}")
    except Exception as e:
        finish_log(conn, args.month, total, "failed", {"error": str(e)})
        print("ETL FAILED:", e)
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
