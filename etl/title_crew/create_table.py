from app.etl.common import get_connection

DDL = """
DROP TABLE IF EXISTS imdb_title_crew;
CREATE TABLE imdb_title_crew (
    tconst    text,
    directors text,
    writers   text
);
"""

conn = get_connection()
with conn, conn.cursor() as cur:
    cur.execute(DDL)

print("[OK] imdb_title_crew создана")