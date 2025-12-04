from app.etl.common import get_connection

DDL = """
DROP TABLE IF EXISTS imdb_title_principals;
CREATE TABLE imdb_title_principals (
    tconst     text,
    ordering   text,
    nconst     text,
    category   text,
    job        text,
    characters text
);
"""

conn = get_connection()
with conn, conn.cursor() as cur:
    cur.execute(DDL)

print("[OK] imdb_title_principals создана")