from django.db import models


class Profession(models.Model):
    """
    Справочник профессий:
    actor, writer, director, producer, cinematographer и т.д.
    Нормализованная таблица.
    """
    name = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
    )

    class Meta:
        db_table = "professions"

    def __str__(self):
        return self.name


class Actor(models.Model):
    """
    Нормализованные актёры.
    IMDb → nconst
    TMDB → tmdb_id
    Все связи через M2M.
    """

    nconst = models.CharField(
        max_length=12,
        unique=True,
        db_index=True,
        help_text="IMDb ID (nconst)",
    )

    tmdb_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="TMDB ID актёра",
    )

    name = models.CharField(max_length=255)

    birth_year = models.IntegerField(
        null=True,
        blank=True,
    )

    death_year = models.IntegerField(
        null=True,
        blank=True,
    )

    professions = models.ManyToManyField(
        Profession,
        through="ActorProfession",
        related_name="actors",
    )

    known_for = models.ManyToManyField(
        "sixmovies.Title",
        related_name="featured_actors",
        blank=True,
    )

    is_voice_actor = models.BooleanField(default=False)

    # Черный список актёров, которые не будут попадать в топ
    blackmark = models.BooleanField(default=False)

    popularity_score = models.FloatField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Агрегированный рейтинг популярности актёра",
    )

    # Версия алгоритма/параметров, по которой считался рейтинг
    popularity_version = models.ForeignKey(
        "sixmovies.PopularityVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="actors",
        help_text="Ссылка на версию расчёта популярности",
    )

    class Meta:
        db_table = "actors"

    def __str__(self):
        return self.name


class ActorProfession(models.Model):
    """
    MANY–TO–MANY между Actor и Profession.
    Именно через отдельную таблицу.
    """

    actor = models.ForeignKey(
        Actor,
        on_delete=models.CASCADE,
        related_name="actor_professions",
    )

    profession = models.ForeignKey(
        Profession,
        on_delete=models.CASCADE,
        related_name="profession_actors",
    )

    class Meta:
        db_table = "actor_professions"
        unique_together = ("actor", "profession")

    def __str__(self):
        return f"{self.actor.name} → {self.profession.name}"



class ActorEdge(models.Model):
    """
    НЕОРИЕНТИРОВАННАЯ связь между двумя актёрами,
    основанная на количестве общих тайтлов (title_principals).

    Создаётся один раз отдельным скриптом:
    - actor_id_low  < actor_id_high  (строгий порядок)
    - weight = количество общих значимых тайтлов
    """

    actor_id_low = models.ForeignKey(
        Actor,
        on_delete=models.CASCADE,
        related_name="edges_low",
        db_column="actor_id_low",
    )

    actor_id_high = models.ForeignKey(
        Actor,
        on_delete=models.CASCADE,
        related_name="edges_high",
        db_column="actor_id_high",
    )

    weight = models.IntegerField(
        default=0,
        help_text="Количество общих тайтлов (clamped ≤ 3 в алгоритме SCS)",
    )

    class Meta:
        db_table = "actor_edges"
        unique_together = ("actor_id_low", "actor_id_high")
        indexes = [
            models.Index(fields=["actor_id_low"]),
            models.Index(fields=["actor_id_high"]),
        ]

    def __str__(self):
        return f"{self.actor_id_low_id}-{self.actor_id_high_id}: {self.weight}"