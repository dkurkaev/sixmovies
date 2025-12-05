import os
import django
import time
from dotenv import load_dotenv

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from sixmovies.models import Actor, Profession, ActorProfession, Title
from django.db import transaction

from etl.db import get_connection

load_dotenv()

BATCH_SIZE = 5000


def normalize_name_basics():
    print("→ Подключаюсь к raw-таблице imdb_name_basics...")
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            nconst,
            primary_name,
            birth_year,
            death_year,
            primary_profession,
            known_for_titles
        FROM imdb_name_basics
    """)

    print("→ Читаю строки стримингом...")
    batch = []
    profession_cache = {p.name: p for p in Profession.objects.all()}
    total = 0
    start = time.time()

    for row in cur:
        (
            nconst,
            primary_name,
            birth_year,
            death_year,
            professions_str,
            known_for_titles_str
        ) = row

        if nconst == "nconst":
            continue

        professions = professions_str.split(",") if professions_str else []
        known_for_titles = known_for_titles_str.split(",") if known_for_titles_str else []

        batch.append({
            "nconst": nconst,
            "name": primary_name,
            "birth_year": int(birth_year) if birth_year else None,
            "death_year": int(death_year) if death_year else None,
            "professions": professions,
            "known_for": known_for_titles,
        })

        if len(batch) >= BATCH_SIZE:
            process_batch(batch, profession_cache)
            total += len(batch)
            print(f"→ обработано {total:,} записей…")
            batch = []

    if batch:
        process_batch(batch, profession_cache)
        total += len(batch)

    print(f"✓ Загружено {total:,} актёров за {time.time() - start:.1f} сек")


def process_batch(batch, profession_cache):
    """Обрабатывает пакет: Actor, Profession, ActorProfession, known_for M2M."""
    # 1) bulk_create Actors
    actors_to_create = [
        Actor(
            nconst=item["nconst"],
            name=item["name"],
            birth_year=item["birth_year"],
            death_year=item["death_year"],
        )
        for item in batch
    ]

    Actor.objects.bulk_create(actors_to_create, ignore_conflicts=True)

    # 2) Вытащим актёров обратно с их PK
    nconsts = [i["nconst"] for i in batch]
    db_actors = {a.nconst: a for a in Actor.objects.filter(nconst__in=nconsts)}

    # 3) Собираем Profession (через таблицу)
    prof_links = []
    new_prof_names = set()

    for item in batch:
        for p in item["professions"]:
            if p not in profession_cache:
                new_prof_names.add(p)

    # создать новые профессии
    if new_prof_names:
        new_prof_objs = [Profession(name=p) for p in new_prof_names]
        Profession.objects.bulk_create(new_prof_objs, ignore_conflicts=True)
        for p in Profession.objects.filter(name__in=new_prof_names):
            profession_cache[p.name] = p

    # линки Actor ↔ Profession
    for item in batch:
        a = db_actors[item["nconst"]]
        for p in item["professions"]:
            prof_links.append(
                ActorProfession(actor_id=a.id, profession_id=profession_cache[p].id)
            )

    ActorProfession.objects.bulk_create(prof_links, ignore_conflicts=True)

    # 4) known_for (M2M: Actor ↔ Title)
    through = Actor.known_for.through
    known_links = []

    # заранее достаём все Title по tconst списком
    all_tconsts = {t for item in batch for t in item["known_for"]}
    db_titles = {t.tconst: t for t in Title.objects.filter(tconst__in=all_tconsts)}

    for item in batch:
        actor = db_actors[item["nconst"]]
        for t in item["known_for"]:
            title = db_titles.get(t)
            if title:
                known_links.append(
                    through(actor_id=actor.id, title_id=title.id)
                )

    through.objects.bulk_create(known_links, ignore_conflicts=True)


if __name__ == "__main__":
    normalize_name_basics()