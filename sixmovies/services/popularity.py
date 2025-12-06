# sixmovies/services/popularity.py

import os
import math
from collections import defaultdict
from typing import Dict, Set, Tuple

import django
from django.db import transaction
from django.db.models import Avg

# При запуске как модуля: python -m sixmovies.services.popularity
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from sixmovies.models import (  # noqa: E402
    Actor,
    Title,
    Genre,
    TitlePrincipal,
    PopularityVersion,
    ActorEdge,
)

# ---------------------------------------------------------------------------
# КОНСТАНТЫ ДЛЯ ФИЛЬТРАЦИИ И БОНУСОВ
# ---------------------------------------------------------------------------

# Минимальное число голосов, чтобы тайтл вообще участвовал в рейтинге актёров.
MIN_VOTES_QUALITY = 2_000

# Пороги голосов для бонуса «глобального хита»
HIT_VOTES_LEVEL_1 = 20_000
HIT_VOTES_LEVEL_2 = 100_000
HIT_VOTES_LEVEL_3 = 500_000

HIT_MULT_LEVEL_1 = 1.5
HIT_MULT_LEVEL_2 = 2.0
HIT_MULT_LEVEL_3 = 3.0


# ---------------------------------------------------------------------------
# ВЕС РОЛИ (MR)
# ---------------------------------------------------------------------------

def _role_weight(ordering: int) -> float:
    """
    Вес роли в титрах.

    ordering=1      → 1.0   (главная роль)
    2–3             → 0.6
    4–7             → 0.3
    >7              → 0.1
    """
    if ordering == 1:
        return 1.0
    if 2 <= ordering <= 3:
        return 0.6
    if 4 <= ordering <= 7:
        return 0.3
    return 0.1


# ---------------------------------------------------------------------------
# ГЛОБАЛЬНЫЕ ПАРАМЕТРЫ КАЧЕСТВА ФИЛЬМОВ
# ---------------------------------------------------------------------------

def _compute_global_rating_params() -> Tuple[float, int]:
    """
    Считает глобальные C и M по базе Title.

    C — средний IMDb рейтинг по всем тайтлам с непустым imdb_rating.
    M — 90-й перцентиль imdb_votes (по всем тайтлам с непустым imdb_votes).

    M используется как сглаживающий параметр:
        vote_factor = V / (V + M)
    """

    qs = Title.objects.exclude(
        imdb_rating__isnull=True
    ).exclude(
        imdb_votes__isnull=True
    )

    agg = qs.aggregate(
        avg_rating=Avg("imdb_rating"),
    )
    C = float(agg["avg_rating"] or 0.0)

    votes = list(
        qs.values_list("imdb_votes", flat=True).order_by("imdb_votes")
    )
    if votes:
        n = len(votes)
        idx = int(0.9 * n) - 1
        if idx < 0:
            idx = 0
        M = int(votes[idx])
        if M <= 0:
            M = 1
    else:
        C = 0.0
        M = 1

    return C, M


# ---------------------------------------------------------------------------
# КАРТА КАЧЕСТВА ТАЙТЛОВ
# ---------------------------------------------------------------------------

def _build_title_quality_map(C: float, M: int) -> Dict[int, float]:
    """
    Предрасчитываем "качество" тайтлов для рейтинга актёров.

    ФИЛЬТРЫ:
      - пропускаем тайтлы без рейтинга или голосов;
      - пропускаем тайтлы с V < MIN_VOTES_QUALITY;
      - пропускаем тайтлы с R <= C (ниже или на уровне среднего рейтинга).

    ДЛЯ ОСТАВШИХСЯ:
        rating_boost  = max(0, R - C)
        vote_factor   = V / (V + M)          (0..1)
        base_q        = vote_factor * rating_boost

    БОНУСЫ ЗА ГЛОБАЛЬНЫЕ ХИТЫ (по числу голосов V):
        V >= HIT_VOTES_LEVEL_3 → × HIT_MULT_LEVEL_3
        V >= HIT_VOTES_LEVEL_2 → × HIT_MULT_LEVEL_2
        V >= HIT_VOTES_LEVEL_1 → × HIT_MULT_LEVEL_1

    В итоге:
        title_quality = base_q * bonus_mult

    Результат: dict title_id -> title_quality (> 0).
    """

    quality: Dict[int, float] = {}

    qs = Title.objects.only("id", "imdb_rating", "imdb_votes")
    processed = 0
    kept = 0

    for t in qs.iterator(chunk_size=5000):
        processed += 1

        if t.imdb_rating is None or t.imdb_votes is None:
            continue

        R = float(t.imdb_rating)
        V = int(t.imdb_votes)

        # 1) минимум голосов для участия
        if V < MIN_VOTES_QUALITY:
            continue

        # 2) фильмы ниже среднего нам не интересны как «легендарные работы»
        rating_boost = R - C
        if rating_boost <= 0.0:
            continue

        # 3) сглаживание по голосам
        denom = V + M
        if denom <= 0:
            continue

        vote_factor = V / denom  # 0..1
        if vote_factor <= 0.0:
            continue

        base_q = vote_factor * rating_boost
        if base_q <= 0.0:
            continue

        # 4) бонус за глобальный хит по числу голосов
        if V >= HIT_VOTES_LEVEL_3:
            bonus_mult = HIT_MULT_LEVEL_3
        elif V >= HIT_VOTES_LEVEL_2:
            bonus_mult = HIT_MULT_LEVEL_2
        elif V >= HIT_VOTES_LEVEL_1:
            bonus_mult = HIT_MULT_LEVEL_1
        else:
            bonus_mult = 1.0

        q = base_q * bonus_mult
        if q <= 0.0:
            continue

        quality[t.id] = q
        kept += 1

    print(
        f"→ title_quality: просмотрено {processed:,} тайтлов, "
        f"оставлено значимых: {kept:,}"
    )
    return quality


# ---------------------------------------------------------------------------
# КАРТА ЖАНРОВ ПО ТАЙТЛАМ
# ---------------------------------------------------------------------------

def _build_title_genres_map() -> Dict[int, Set[str]]:
    """
    Предрасчитываем жанры для каждого тайтла.

    dict: title_id -> {genre_name1, genre_name2, ...}
    """

    title_genres: Dict[int, Set[str]] = defaultdict(set)

    through = Title.genres.through  # M2M-таблица titles_genres
    qs = through.objects.select_related("genre").only("title_id", "genre")
    for row in qs.iterator(chunk_size=5000):
        title_id = row.title_id
        genre = row.genre
        if isinstance(genre, Genre):
            title_genres[title_id].add(genre.name)

    return title_genres


# ---------------------------------------------------------------------------
# НОРМАЛИЗАЦИЯ КОМПОНЕНТОВ
# ---------------------------------------------------------------------------

def _normalize_component(values: Dict[int, float]) -> Dict[int, float]:
    """
    Приводим значения компонента к диапазону [0; 1] через min–max.

    Если все значения одинаковые — всем ставим 0.5.
    Если словарь пустой — возвращаем пустой.
    """
    if not values:
        return {}

    all_vals = list(values.values())
    min_v = min(all_vals)
    max_v = max(all_vals)

    if max_v > min_v:
        scale = 1.0 / (max_v - min_v)
        return {
            key: (val - min_v) * scale
            for key, val in values.items()
        }

    # все одинаковые
    return {key: 0.5 for key in values.keys()}


# ---------------------------------------------------------------------------
# ОСНОВНОЙ РАСЧЁТ ПОПУЛЯРНОСТИ АКТЁРОВ
# ---------------------------------------------------------------------------

@transaction.atomic
def recalc_actor_popularity(
    w_role: float = 0.15,
    w_quality: float = 0.65,
    w_reach: float = 0.20,
    notes: str = "",
) -> PopularityVersion:
    """
    Пересчитывает рейтинг популярности актёров.

    Общая схема:

      1) Предрасчитываем C, M, title_quality и жанры по тайтлам.
      2) Идём по TitlePrincipal (только category in ['actor','actress']),
         НО УЧИТЫВАЕМ ТОЛЬКО ТЕ СТРОКИ, ГДЕ title_quality[title_id] существует.
         То есть «маленькие» локальные работы с малым числом голосов и
         средним/низким рейтингом просто не попадают в расчёт.

      3) Для каждого актёра:

         S_role_raw(actor)    = log(1 + Σ role_weight)
         S_quality_raw(actor) = log(1 + Σ role_weight * title_quality)
         S_reach_raw(actor)   = log(1 + #genres) + 0.5 * log(1 + roles_count)

      4) Каждый компонент нормализуем в [0;1] по min–max:

         S_role_norm, S_quality_norm, S_reach_norm

      5) Итоговый базовый score_01(actor):

         score_01 = w_role * S_role_norm +
                     w_quality * S_quality_norm +
                     w_reach * S_reach_norm

         popularity_score = score_01 * 1000

      6) Дополнительно считаем SCS (Star Connectivity Score) по графу связей
         между актёрами через actor_edges (actor_id_low, actor_id_high, weight),
         причём вес связи с каждым соседом жёстко пессимизируется
         по популярности соседа:

             neigh_pop = popularity_score(neighbor) / 1000
             star_factor = neigh_pop ** 6
             edge_weight = log(1 + min(shared_count, 3))
             вклад = edge_weight * star_factor

         SCS нормализуем в 0–1000 и комбинируем:

             combined = 0.5 * popularity_score + 0.5 * scs_norm

      7) Дополнительные корректировки:
         - age-пессимизация по качественно-взвешенному среднему году:
               mean_hit_year < 1970  → ×0.10
               1970 ≤ mean_hit_year < 1985 → ×0.35
               1985 ≤ mean_hit_year < 2000 → ×0.75
               ≥ 2000 → ×1.0
         - выкидываем voice-актеров (is_voice_actor = TRUE);
         - manual flags:
               blackmark → итоговый рейтинг = 0
               wildcard  → мягкий буст (×1.3, но не выше 1000)
    """

    # 1. глобальные параметры качества фильмов
    C, M = _compute_global_rating_params()
    print(f"→ глобальные параметры: C={C:.4f}, M={M}")

    # 2. фиксируем версию расчёта
    version = PopularityVersion.objects.create(
        weight_role=w_role,
        weight_quality=w_quality,
        weight_reach=w_reach,
        global_mean_rating=C,
        min_votes_for_weight=M,
        notes=notes or (
            f"actor popularity recalculation "
            f"(MIN_VOTES_QUALITY={MIN_VOTES_QUALITY}, "
            f"hit thresholds={HIT_VOTES_LEVEL_1}/"
            f"{HIT_VOTES_LEVEL_2}/{HIT_VOTES_LEVEL_3}, "
            f"SCS pow(6), age penalty by mean hit year, "
            f"voice filter, blackmark/wildcard)"
        ),
    )

    # 3. предрасчёт title_quality и жанров
    title_quality = _build_title_quality_map(C, M)
    title_genres = _build_title_genres_map()

    if not title_quality:
        print("! title_quality пустой — ничего не считаем")
        return version

    # 4. агрегаты по актёрам (только по значимым тайтлам!)
    role_sum: Dict[int, float] = defaultdict(float)        # Σ role_weight
    quality_sum: Dict[int, float] = defaultdict(float)     # Σ role_weight * title_quality
    roles_count: Dict[int, int] = defaultdict(int)         # количество principal-записей
    actor_genres: Dict[int, Set[str]] = defaultdict(set)   # множество жанров

    # Для age-пессимизации: качественно-взвешенный средний год
    # на основе веса w = title_quality * role_weight.
    year_weight_sum: Dict[int, float] = defaultdict(float)
    year_weight_mass: Dict[int, float] = defaultdict(float)

    principals_qs = (
        TitlePrincipal.objects
        .select_related("title", "actor")
        .filter(category__in=["actor", "actress"])
        .only("id", "actor_id", "title_id", "ordering", "title__start_year")
    )

    processed = 0
    used_principals = 0

    for tp in principals_qs.iterator(chunk_size=10000):
        processed += 1
        title_id = tp.title_id

        # берем только тайтлы, у которых есть предрасчитанное качество
        tq = title_quality.get(title_id)
        if tq is None:
            continue

        used_principals += 1
        actor_id = tp.actor_id
        mr = _role_weight(tp.ordering)

        # 1) роль: аккумулируем суммарную «важность ролей»
        role_sum[actor_id] += mr

        # 2) качество
        quality_sum[actor_id] += mr * tq

        # 3) охват: количество записей и уникальные жанры
        roles_count[actor_id] += 1
        for g in title_genres.get(title_id, ()):
            actor_genres[actor_id].add(g)

        # 4) age-профиль: w = tq * mr, на нём считаем средний год
        start_year = getattr(tp.title, "start_year", None)
        if start_year is not None:
            w = tq * mr
            year_weight_sum[actor_id] += start_year * w
            year_weight_mass[actor_id] += w

        if processed % 1_000_000 == 0:
            print(
                f"→ просмотрено {processed:,} principal-записей, "
                f"взято значимых: {used_principals:,}"
            )

    print(
        f"→ итог: просмотрено {processed:,} principal-записей, "
        f"использовано (по значимым тайтлам): {used_principals:,}"
    )

    if not role_sum:
        print("! нет актёров с посчитанными ролями — выходим")
        return version

    # 5. формируем сырые компоненты S_role_raw, S_quality_raw, S_reach_raw
    actor_ids = (
        set(role_sum.keys())
        | set(quality_sum.keys())
        | set(roles_count.keys())
        | set(actor_genres.keys())
    )

    s_role_raw: Dict[int, float] = {}
    s_quality_raw: Dict[int, float] = {}
    s_reach_raw: Dict[int, float] = {}

    for actor_id in actor_ids:
        # S_role_raw = log(1 + Σ role_weight)
        r_sum = role_sum.get(actor_id, 0.0)
        s_role_raw[actor_id] = math.log1p(r_sum) if r_sum > 0.0 else 0.0

        # S_quality_raw = log(1 + Σ role_weight * title_quality)
        q_sum = quality_sum.get(actor_id, 0.0)
        s_quality_raw[actor_id] = math.log1p(q_sum) if q_sum > 0.0 else 0.0

        # S_reach_raw = log(1 + #genres) + 0.5 * log(1 + roles_count)
        genres_set = actor_genres.get(actor_id, set())
        n_genres = len(genres_set)
        gv = math.log1p(n_genres) if n_genres > 0 else 0.0

        n_roles = roles_count.get(actor_id, 0)
        fv = math.log1p(n_roles) if n_roles > 0 else 0.0

        s_reach_raw[actor_id] = gv + 0.5 * fv

    # 5.1. считаем mean_hit_year по качественно-взвешенному профилю
    mean_hit_year: Dict[int, float] = {}
    for actor_id in actor_ids:
        mass = year_weight_mass.get(actor_id, 0.0)
        if mass > 0.0:
            mean_hit_year[actor_id] = year_weight_sum[actor_id] / mass

    # 6. нормализуем каждый компонент в [0;1]
    s_role_norm = _normalize_component(s_role_raw)
    s_quality_norm = _normalize_component(s_quality_raw)
    s_reach_norm = _normalize_component(s_reach_raw)

    # 7. базовый score_01 и шкала 0–1000 (первичный popularity_score)
    base_popularity: Dict[int, float] = {}
    for actor_id in actor_ids:
        sr = s_role_norm.get(actor_id, 0.0)
        sq = s_quality_norm.get(actor_id, 0.0)
        srh = s_reach_norm.get(actor_id, 0.0)

        score_01 = (
            w_role * sr +
            w_quality * sq +
            w_reach * srh
        )
        if score_01 < 0.0:
            score_01 = 0.0
        elif score_01 > 1.0:
            score_01 = 1.0

        base_popularity[actor_id] = score_01 * 1000.0

    print(f"→ получено {len(base_popularity):,} актёров с базовым рейтингом")

    if not base_popularity:
        print("! нет актёров с нормализованными рейтингами — выходим")
        return version

    # ------------------------------------------------------------------
    # ДОПОЛНИТЕЛЬНЫЙ ЭТАП: Star Connectivity Score (SCS)
    # ------------------------------------------------------------------

    print("→ начинаем расчёт connectivity (SCS)…")

    # 1. Загружаем популярность в память
    actor_pop = base_popularity  # 0..1000 базовые популярности

    # 1.1. Загружаем флаги актёров (voice, blackmark, wildcard)
    voice_flags: Dict[int, bool] = {}
    black_flags: Dict[int, bool] = {}
    wildcard_flags: Dict[int, bool] = {}

    for actor_id, is_voice, blackmark, wildcard in (
        Actor.objects
        .filter(id__in=actor_pop.keys())
        .values_list("id", "is_voice_actor", "blackmark", "wildcard")
    ):
        voice_flags[actor_id] = bool(is_voice)
        black_flags[actor_id] = bool(blackmark)
        wildcard_flags[actor_id] = bool(wildcard)

    # 2. Загружаем actor_edges через ORM:
    #    actor_id_low_id, actor_id_high_id, weight
    edges = []
    for edge in ActorEdge.objects.only("actor_id_low", "actor_id_high", "weight").iterator(chunk_size=100000):
        a = edge.actor_id_low_id
        b = edge.actor_id_high_id
        w = edge.weight
        # Пропускаем актёров без базовой популярности (не попали в фильтр)
        if a in actor_pop and b in actor_pop:
            edges.append((a, b, w))

    # 3. Строим двунаправленный граф
    graph: Dict[int, list] = defaultdict(list)
    for a, b, w in edges:
        shared = min(int(w), 3)
        if shared <= 0:
            continue
        edge_weight = math.log1p(shared)
        graph[a].append((b, edge_weight))
        graph[b].append((a, edge_weight))

    # 4. SCS RAW
    scs_raw: Dict[int, float] = defaultdict(float)

    for actor_id, neighbors in graph.items():
        for neighbor_id, edge_w in neighbors:
            neigh_pop_01 = actor_pop.get(neighbor_id, 0.0) / 1000.0
            if neigh_pop_01 <= 0.0:
                continue
            # ЖЁСТКАЯ ПЕССИМИЗАЦИЯ: степень 6
            star_factor = neigh_pop_01 ** 6
            if star_factor <= 0.0:
                continue
            scs_raw[actor_id] += edge_w * star_factor

    # 5. Нормализация SCS в 0–1000
    if scs_raw:
        vals = list(scs_raw.values())
        min_v = min(vals)
        max_v = max(vals)
        if max_v > min_v:
            scs_norm: Dict[int, float] = {
                k: 1000.0 * (v - min_v) / (max_v - min_v)
                for k, v in scs_raw.items()
            }
        else:
            scs_norm = {k: 500.0 for k in scs_raw}
    else:
        scs_norm = {}

    print("→ SCS посчитан, объединяем с базовой популярностью…")

    # 6. Комбинированный финальный рейтинг + возраст + manual flags
    final_scores: Dict[int, float] = {}
    for actor_id, pop in actor_pop.items():
        scs_val = scs_norm.get(actor_id, 0.0)
        final = 0.5 * pop + 0.5 * scs_val

        # age-пессимизация по mean_hit_year
        year = mean_hit_year.get(actor_id)
        if year is None:
            age_factor = 1.0
        elif year < 1970:
            age_factor = 0.10
        elif year < 1985:
            age_factor = 0.35
        elif year < 2000:
            age_factor = 0.75
        else:
            age_factor = 1.0

        final *= age_factor

        # manual blackmark → выкинуть
        if black_flags.get(actor_id):
            final = 0.0

        # manual wildcard → мягкий буст (но не выше 1000)
        if wildcard_flags.get(actor_id) and final > 0.0:
            final *= 1.3
            if final > 1000.0:
                final = 1000.0

        # выкидываем voice-актеров из финального рейтинга
        if voice_flags.get(actor_id):
            final = 0.0

        final_scores[actor_id] = final

    normalized_scores = final_scores

    print(f"→ получено {len(normalized_scores):,} актёров с финальным рейтингом")

    # 7. Обновляем актёров пачками
    actor_ids_list = list(normalized_scores.keys())
    total_actors = len(actor_ids_list)

    BATCH = 10_000
    for i in range(0, total_actors, BATCH):
        batch_ids = actor_ids_list[i:i + BATCH]
        actors = Actor.objects.filter(id__in=batch_ids)

        for actor in actors:
            actor.popularity_score = normalized_scores.get(actor.id, 0.0)
            actor.popularity_version = version

        Actor.objects.bulk_update(
            actors,
            fields=["popularity_score", "popularity_version"],
            batch_size=1000,
        )
        print(
            f"→ обновлены актёры {i + 1:,}–{i + len(batch_ids):,} "
            f"из {total_actors:,}"
        )

    print("✓ расчёт рейтингов актёров завершён "
          "(quality + hits + SCS pow(6) + age penalty by mean year "
          "+ voice-filter + blackmark/wildcard)")
    return version


# ---------------------------------------------------------------------------
# Запуск как модуля
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    recalc_actor_popularity(
        w_role=0.15,
        w_quality=0.70,
        w_reach=0.15,
        notes="hard cut low-vote titles, boost global hits, "
              "SCS pow(6), age penalty by mean year, voice-filter, blackmark/wildcard",
    )