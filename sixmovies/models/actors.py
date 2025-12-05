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

    class Meta:
        db_table = "actors"

    def __str__(self):
        return self.name


class ActorProfession(models.Model):
    """
    MANY–TO–MANY между Actor и Profession.
    Именно через отдельную таблицу, потому что она нормализованная,
    и потому что мы можем потом добавить:
    - приоритет профессии
    - роль в конкретном фильме
    - источник данных (IMDb/TMDB)
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