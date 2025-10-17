import os
from math import ceil
from flask import Flask, render_template, request
from dotenv import load_dotenv
import pymysql

def _req(name: str) -> str:
    v = os.getenv(name)
    if not v: raise RuntimeError(f"Missing required env var: {name}")
    return v

def get_db():
    load_dotenv()
    return pymysql.connect(
        host=_req("DB_HOST"),
        port=int(os.getenv("DB_PORT","3306")),
        user=_req("DB_USER"),
        password=_req("DB_PASSWORD"),
        database=_req("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

def create_app():
    app = Flask(__name__)

    @app.route("/health")
    def health():
        return "OK", 200

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/search")
    def search():
        start = request.args.get("start")
        end = request.args.get("end")
        borough = request.args.get("borough") or ""
        complaint = request.args.get("complaint") or ""
        page = int(request.args.get("page", 1))
        page_size = 20

        where = []
        params = []
        if start and end:
            where.append("created_datetime BETWEEN %s AND %s")
            params.extend([start, end])
        if borough:
            where.append("borough = %s")
            params.append(borough)
        if complaint:
            where.append("complaint_type LIKE %s")
            params.append(f"%{complaint}%")

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        offset = (page-1)*page_size

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) AS c FROM service_requests {where_sql}", params)
                total = cur.fetchone()["c"]

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT request_id, created_datetime, borough, complaint_type, descriptor, status
                        FROM service_requests {where_sql}
                        ORDER BY created_datetime DESC
                        LIMIT %s OFFSET %s""",
                    params + [page_size, offset]
                )
                rows = cur.fetchall()

        pages = ceil(total / page_size) if page_size else 1
        return render_template("results.html",
          rows=rows, total=total, page=page, pages=pages,
          start=start, end=end, borough=borough, complaint=complaint)

    @app.route("/aggregate/borough")
    def aggregate_borough():
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT borough, COUNT(*) AS total
                    FROM service_requests
                    GROUP BY borough
                    ORDER BY total DESC
                """)
                agg = cur.fetchall()
        return render_template("aggregate.html", agg=agg, title="Complaints per Borough")

    return app

app = create_app()
