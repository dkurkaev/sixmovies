from app.etl.common import get_connection

DDL = """
DROP TABLE IF EXISTS imdb_title_ratings;
CREATE TABLE imdb_title_ratings (
    tconst         text,
    average_rating text,
    num_votes      text
);
"""

conn = get_connection()
with conn, conn.cursor() as cur:
    cur.execute(DDL)

print("[OK] imdb_title_ratings создана")