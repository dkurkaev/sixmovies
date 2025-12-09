from app.etl.common import get_connection

DDL = """
DROP TABLE IF EXISTS imdb_name_basics;
CREATE TABLE imdb_name_basics (
    nconst             text,
    primary_name       text,
    birth_year         text,
    death_year         text,
    primary_profession text,
    known_for_titles   text
);
"""

conn = get_connection()
with conn, conn.cursor() as cur:
    cur.execute(DDL)

print("[OK] imdb_name_basics создана")