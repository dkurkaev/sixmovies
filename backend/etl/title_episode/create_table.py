from app.etl.common import get_connection

DDL = """
DROP TABLE IF EXISTS imdb_title_episode;
CREATE TABLE imdb_title_episode (
    tconst         text,
    parent_tconst  text,
    season_number  text,
    episode_number text
);
"""

conn = get_connection()
with conn, conn.cursor() as cur:
    cur.execute(DDL)

print("[OK] imdb_title_episode создана")