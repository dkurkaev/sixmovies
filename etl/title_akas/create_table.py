from app.etl.common import get_connection

DDL = """
DROP TABLE IF EXISTS imdb_title_akas;
CREATE TABLE imdb_title_akas (
    title_id           text,
    ordering           text,
    title              text,
    region             text,
    language           text,
    types              text,
    attributes         text,
    is_original_title  text
);
"""

conn = get_connection()
with conn, conn.cursor() as cur:
    cur.execute(DDL)
print("[OK] imdb_title_akas создана.")