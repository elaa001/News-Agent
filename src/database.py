import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "prosicht"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD")
    )

def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            company VARCHAR(255),
            event_type VARCHAR(100),
            sector VARCHAR(255),
            from_country VARCHAR(100),
            to_country VARCHAR(100),
            investment_usd BIGINT,
            jobs_created INT,
            jobs_lost INT,
            bios_score INT,
            recommended_action VARCHAR(50),
            rationale TEXT,
            summary TEXT,
            article_summary TEXT,
            source_url TEXT,
            fetched_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Table created successfully.")

def save_event(event: dict):
    conn = get_connection()
    cur = conn.cursor()
    bios = event.get("bios_fit") or {}
    
    cur.execute("""
        INSERT INTO events (
            company, event_type, sector,
            from_country, to_country,
            investment_usd, jobs_created, jobs_lost,
            bios_score, recommended_action, rationale,
            summary, article_summary, source_url
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """, (
        (event.get("company") or {}).get("name"),
        event.get("event_type"),
        event.get("sector"),
        (event.get("from_location") or {}).get("country"),
        (event.get("to_location") or {}).get("country"),
        (event.get("investment_size") or {}).get("amount"),
        (event.get("jobs") or {}).get("created"),
        (event.get("jobs") or {}).get("lost"),
        bios.get("score"),
        bios.get("recommended_action"),
        bios.get("rationale"),
        event.get("summary"),
        event.get("article_summary"),
        event.get("source_url"),
    ))
    conn.commit()

    if cur.rowcount == 0:
        print(f"  [DB] Already exists, skipped.")
    else:
        print(f"  [DB] Saved to database.")

    cur.close()
    conn.close()

def load_all_events():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM events ORDER BY fetched_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows