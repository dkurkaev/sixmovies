import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
IMDB_DATA_DIR = Path(os.getenv("IMDB_DATA_DIR"))

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=DictCursor,
    )

def safe_copy(path: Path, table: str):
    print(f"[LOAD] {path.name} → {table}")
    conn = get_connection()

    try:
        with conn.cursor() as cur, open(path, "r", encoding="utf-8") as f:

            sql = (
                f"COPY {table} FROM STDIN "
                "WITH (FORMAT text, DELIMITER E'\\t', NULL '\\N')"
            )

            try:
                # быстрая попытка COPY
                cur.copy_expert(sql, f)
                conn.commit()
                print(f"[OK] Быстрый COPY успешно выполнен.")
                return

            except Exception:
                print("[WARN] COPY упал, fallback режим...")

                f.seek(0)
                header = next(f)

                total = 0
                bad = 0

                for line_num, line in enumerate(f, start=2):
                    total += 1
                    try:
                        cur.copy_expert(sql, line)
                    except Exception:
                        bad += 1
                        continue

                conn.commit()
                print(f"[DONE] fallback завершён. Всего: {total}, плохих строк: {bad}")

    finally:
        conn.close()