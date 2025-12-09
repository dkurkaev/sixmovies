from app.etl.common import IMDB_DATA_DIR, safe_copy

safe_copy(IMDB_DATA_DIR / "title.crew.tsv", "imdb_title_crew")