from pathlib import Path
from app.etl.common import IMDB_DATA_DIR, safe_copy

FILE = IMDB_DATA_DIR / "title.akas.tsv"

safe_copy(FILE, "imdb_title_akas")