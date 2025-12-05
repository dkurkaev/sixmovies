import os
import django
import time
from dotenv import load_dotenv

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from sixmovies.models import Title
from etl.db import get_connection
from django.db import transaction

load_dotenv()

BATCH_SIZE = 50000


def normalize_ratings():
    print("→ Читаю imdb_title_ratings стримингом…")
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            tconst,
            average_rating,
            num_votes
        FROM imdb_title_ratings
    """)

    batch = []
    updated = 0
    skipped = 0

    start = time.time()

    for row in cur:
        tconst, rating, votes = row

        if tconst == "tconst":
            continue  # пропускаем заголовок

        batch.append({
            "tconst": tconst,
            "rating": float(rating) if rating else None,
            "votes": int(votes) if votes else None
        })

        if len(batch) >= BATCH_SIZE:
            upd = process_batch(batch)
            updated += upd["updated"]
            skipped += upd["skipped"]
            print(f"✓ обновлено {updated:,} | пропущено {skipped:,}")
            batch.clear()

    if batch:
        upd = process_batch(batch)
        updated += upd["updated"]
        skipped += upd["skipped"]

    print("\n===== Готово =====")
    print(f"✓ обновлено: {updated:,}")
    print(f"⚠️ пропущено (нет title): {skipped:,}")
    print(f"⏱ время: {time.time() - start:.1f} сек")


def process_batch(batch):
    """Обновляет imdb_rating и imdb_votes у Title."""
    tconsts = [item["tconst"] for item in batch]
    titles = {t.tconst: t for t in Title.objects.filter(tconst__in=tconsts)}

    to_update = []
    skipped = 0

    for item in batch:
        t = titles.get(item["tconst"])
        if not t:
            skipped += 1
            continue
        t.imdb_rating = item["rating"]
        t.imdb_votes = item["votes"]
        to_update.append(t)

    if to_update:
        Title.objects.bulk_update(to_update, ["imdb_rating", "imdb_votes"])

    return {"updated": len(to_update), "skipped": skipped}


if __name__ == "__main__":
    normalize_ratings()