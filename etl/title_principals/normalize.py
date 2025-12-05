import os
import django
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction
from sixmovies.models import Actor, Title, TitlePrincipal, TitlePrincipalCharacter
from etl.db import get_connection


BATCH_SIZE = 5000


def normalize_principals():
    print("→ Читаю raw-таблицу imdb_title_principals стримингом...")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            tconst,
            ordering,
            nconst,
            category,
            job,
            characters
        FROM imdb_title_principals
    """)

    batch = []
    total = 0
    start = time.time()

    for row in cur:
        (
            tconst,
            ordering,
            nconst,
            category,
            job,
            chars_json,
        ) = row

        if tconst == "tconst":
            continue  # пропускаем заголовок

        # characters: ['Spider-Man', 'Peter Parker'] → список строк
        if chars_json:
            chars_json = chars_json.strip()
            chars_json = chars_json.strip("{}[]")
            if chars_json:
                characters = [c.strip().strip('"') for c in chars_json.split(",")]
            else:
                characters = []
        else:
            characters = []

        batch.append({
            "tconst": tconst,
            "nconst": nconst,
            "ordering": int(ordering) if ordering else None,
            "category": category,
            "job": job if job else None,
            "characters": characters,
        })

        if len(batch) >= BATCH_SIZE:
            process_batch(batch)
            total += len(batch)
            print(f"→ обработано {total:,} записей…")
            batch = []

    if batch:
        process_batch(batch)
        total += len(batch)

    print(f"✓ principals загрузились: {total:,} строк за {time.time() - start:.1f} сек")


def process_batch(batch):
    """Сохраняем TitlePrincipal + TitlePrincipalCharacter в базу."""
    title_cache = {}
    actor_cache = {}

    # вытягиваем все tconst и nconst
    tconsts = {item["tconst"] for item in batch}
    nconsts = {item["nconst"] for item in batch}

    # заранее грузим Title
    for t in Title.objects.filter(tconst__in=tconsts):
        title_cache[t.tconst] = t

    # заранее грузим Actor
    for a in Actor.objects.filter(nconst__in=nconsts):
        actor_cache[a.nconst] = a

    principals_to_create = []
    characters_to_create = []

    for item in batch:
        title = title_cache.get(item["tconst"])
        actor = actor_cache.get(item["nconst"])

        if not title or not actor:
            continue

        principal = TitlePrincipal(
            title_id=title.id,
            actor_id=actor.id,
            ordering=item["ordering"] or 0,
            category=item["category"],
            job=item["job"],
        )
        principals_to_create.append(principal)

    # сохраняем principals
    TitlePrincipal.objects.bulk_create(principals_to_create, ignore_conflicts=True)

    # теперь надо получить id-шники только что созданных principals
    # используем повторный выбор по (title, actor, ordering)
    lookup_keys = [
        (p.title_id, p.actor_id, p.ordering)
        for p in principals_to_create
    ]

    db_principals = {}
    for p in TitlePrincipal.objects.filter(
        title_id__in=[k[0] for k in lookup_keys],
        actor_id__in=[k[1] for k in lookup_keys]
    ):
        db_principals[(p.title_id, p.actor_id, p.ordering)] = p.id

    # создаём characters
    for item in batch:
        tconst = item["tconst"]
        nconst = item["nconst"]
        ordering = item["ordering"] or 0

        title = title_cache.get(tconst)
        actor = actor_cache.get(nconst)

        if not title or not actor:
            continue

        pkey = (title.id, actor.id, ordering)
        principal_id = db_principals.get(pkey)
        if not principal_id:
            continue

        for cname in item["characters"]:
            if cname.strip():
                characters_to_create.append(
                    TitlePrincipalCharacter(
                        principal_id=principal_id,
                        character_name=cname,
                    )
                )

    TitlePrincipalCharacter.objects.bulk_create(characters_to_create, ignore_conflicts=True)


if __name__ == "__main__":
    normalize_principals()

    