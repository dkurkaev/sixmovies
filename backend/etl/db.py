from contextlib import contextmanager
from typing import Iterator, Any

import psycopg2
from psycopg2.extras import DictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        cursor_factory=DictCursor,
    )

@contextmanager
def get_cursor(commit: bool = False) -> Iterator[Any]:
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                yield cur
            if commit:
                conn.commit()
    finally:
        conn.close()