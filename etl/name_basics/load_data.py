from app.etl.common import IMDB_DATA_DIR, safe_copy

safe_copy(IMDB_DATA_DIR / "name.basics.tsv", "imdb_name_basics")