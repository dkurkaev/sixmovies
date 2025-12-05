import os
import csv
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
ERROR_LOG = "etl_errors_name_basics.csv"


# -----------------------
# 🔥 ЛОГИРОВАНИЕ ОШИБОК
# -----------------------
def log_error(nconst, reason, row):
    """Пишет ошибки в CSV для анализа."""
    with open(ERROR_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([nconst, reason, *row])


# -----------------------
# 🔥 ОСНОВНАЯ ЛОГИКА
# -----------------------
def normalize_name_basics():
    print("→ Подключаюсь к raw-таблице imdb_name_basics...")
    conn = get_connection()
    cur = conn.cursor()

    # создаём CSV, если его нет
    if not os.path.exists(ERROR_LOG):
        with open(ERROR_LOG, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["nconst", "error_reason", "raw_row"])

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

        # 1) Заголовок
        if nconst == "nconst":
            continue

        # 2) Нет имени → логируем
        if not primary_name or primary_name == "\\N":
            log_error(nconst, "EMPTY_NAME", row)
            continue

        # 3) ошибки парсинга birth_year
        try:
            by = int(birth_year) if birth_year and birth_year.isdigit() else None
        except Exception:
            log_error(nconst, "INVALID_BIRTH_YEAR", row)
            by = None

        # 4) ошибки парсинга death_year
        try:
            dy = int(death_year) if death_year and death_year.isdigit() else None
        except Exception:
            log_error(nconst, "INVALID_DEATH_YEAR", row)
            dy = None

        # 5) Профессии, безопасно
        professions = []
        if professions_str:
            for p in professions_str.split(","):
                p = p.strip()
                if p:
                    professions.append(p)
                else:
                    log_error(nconst, "EMPTY_PROFESSION", row)

        # 6) known_for_titles, безопасно
        known_for_titles = []
        if known_for_titles_str:
            for t in known_for_titles_str.split(","):
                t = t.strip()
                if t:
                    known_for_titles.append(t)
                else:
                    log_error(nconst, "EMPTY_KNOWN_FOR_ENTRY", row)

        batch.append({
            "nconst": nconst,
            "name": primary_name,
            "birth_year": by,
            "death_year": dy,
            "professions": professions,
            "known_for": known_for_titles,
        })

        if len(batch) >= BATCH_SIZE:
            process_batch(batch, profession_cache)
            total += len(batch)
            print(f"→ обработано {total:,} записей…")
            batch = []

    # остаток
    if batch:
        process_batch(batch, profession_cache)
        total += len(batch)

    print(f"✓ Загружено {total:,} актёров за {time.time() - start:.1f} сек")
    print(f"⚠ Ошибочные строки записаны в {ERROR_LOG}")


# -----------------------
# 🔥 ОБРАБОТКА ПАКЕТОВ
# -----------------------
def process_batch(batch, profession_cache):

    # 1) Создание Actor
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

    # 2) lookup актёров
    nconsts = [i["nconst"] for i in batch]
    db_actors = {a.nconst: a for a in Actor.objects.filter(nconst__in=nconsts)}

    # 3) профессии
    new_prof_names = set()

    for item in batch:
        for p in item["professions"]:
            if p and p not in profession_cache:
                new_prof_names.add(p)

    if new_prof_names:
        Profession.objects.bulk_create([Profession(name=p) for p in new_prof_names])
        for p in Profession.objects.filter(name__in=new_prof_names):
            profession_cache[p.name] = p

    # 4) Actor ↔ Profession
    prof_links = []
    for item in batch:
        actor = db_actors[item["nconst"]]
        for p in item["professions"]:
            prof_links.append(
                ActorProfession(
                    actor_id=actor.id,
                    profession_id=profession_cache[p].id
                )
            )

    ActorProfession.objects.bulk_create(prof_links, ignore_conflicts=True)

    # 5) Actor ↔ Title (known_for)
    through = Actor.known_for.through
    known_links = []

    all_tconsts = {t for item in batch for t in item["known_for"] if t}
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