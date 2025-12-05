import os
import django
import time
from dotenv import load_dotenv

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction
from sixmovies.models import Title, Genre

load_dotenv()

BATCH_SIZE = 5000


def normalize_titles():
    from etl.db import get_connection  # импорт внутри функции — важно

    print("→ Подключаюсь к raw-таблице imdb_title_basics...")
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT tconst, title_type, primary_title, original_title,
               is_adult, start_year, end_year, runtime_minutes, genres
        FROM imdb_title_basics
        WHERE title_type IN ('movie', 'tvSeries')
    """)

    print("→ Читаю строки стримингом...")

    batch = []
    genre_cache = {g.name: g for g in Genre.objects.all()}
    total = 0
    start_time = time.time()

    for row in cur:
        (
            tconst,
            title_type,
            primary_title,
            original_title,
            is_adult,
            start_year,
            end_year,
            runtime_minutes,
            genres_str,
        ) = row

        batch.append({
            "tconst": tconst,
            "title_type": title_type,
            "primary_title": primary_title,
            "original_title": original_title,
            "is_adult": bool(is_adult),
            "start_year": int(start_year) if start_year else None,
            "end_year": int(end_year) if end_year else None,
            "runtime_minutes": int(runtime_minutes) if runtime_minutes else None,
            "genres": genres_str.split(",") if genres_str else [],
        })

        if len(batch) >= BATCH_SIZE:
            process_batch(batch, genre_cache)
            total += len(batch)
            print(f"→ обработано {total:,} записей")
            batch = []

    if batch:
        process_batch(batch, genre_cache)
        total += len(batch)

    print(f"✓ Загружено {total:,} тайтлов за {time.time() - start_time:.1f} сек")


def process_batch(batch, genre_cache):
    # 1) сохраняем Title
    objs = [
        Title(
            tconst=item["tconst"],
            title_type=item["title_type"],
            primary_title=item["primary_title"],
            original_title=item["original_title"],
            is_adult=item["is_adult"],
            start_year=item["start_year"],
            end_year=item["end_year"],
            runtime_minutes=item["runtime_minutes"],
        )
        for item in batch
    ]

    Title.objects.bulk_create(objs, ignore_conflicts=True)

    # 2) вытягиваем обратно с PK
    tconsts = [i["tconst"] for i in batch]
    db_titles = {t.tconst: t for t in Title.objects.filter(tconst__in=tconsts)}

    # 3) подготавливаем связи
    through = Title.genres.through
    m2m = []

    for item in batch:
        t = db_titles[item["tconst"]]
        for g in item["genres"]:
            if g not in genre_cache:
                genre_cache[g] = Genre.objects.create(name=g)

            m2m.append(through(title_id=t.id, genre_id=genre_cache[g].id))

    # 4) массовая вставка M2M
    through.objects.bulk_create(m2m, ignore_conflicts=True)


if __name__ == "__main__":
    normalize_titles()