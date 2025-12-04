from app.etl.common import get_connection

DDL = """
DROP TABLE IF EXISTS imdb_title_basics;
CREATE TABLE imdb_title_basics (
    tconst          text,
    title_type      text,
    primary_title   text,
    original_title  text,
    is_adult        text,
    start_year      text,
    end_year        text,
    runtime_minutes text,
    genres          text
);
"""

conn = get_connection()
with conn, conn.cursor() as cur:
    cur.execute(DDL)

print("[OK] imdb_title_basics создана")