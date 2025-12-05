from django.db import models


class Genre(models.Model):
    """
    Нормализованный справочник жанров:
    Action, Drama, Sci-Fi, Romance...
    """
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = "genres"

    def __str__(self):
        return self.name


class Title(models.Model):
    """
    Универсальная сущность фильма/сериала/тв фильма/анимации.
    """
    id = models.BigAutoField(primary_key=True)

    tconst = models.CharField(
        max_length=12,
        unique=True,
        db_index=True,
        help_text="IMDb ID, например 'tt0468569'"
    )

    tmdb_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="TMDB ID фильма/сериала"
    )

    title_type = models.CharField(
        max_length=32,
        db_index=True,
        help_text="movie, tvSeries, tvMovie, short, tvEpisode, etc."
    )

    primary_title = models.CharField(max_length=512)
    original_title = models.CharField(max_length=512)

    is_adult = models.BooleanField(default=False)

    start_year = models.IntegerField(null=True, blank=True)
    end_year = models.IntegerField(null=True, blank=True)

    runtime_minutes = models.IntegerField(null=True, blank=True)

    genres = models.ManyToManyField(
        Genre,
        related_name="titles",
        blank=True
    )

    imdb_rating = models.FloatField(null=True, blank=True)
    imdb_votes = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "titles"
        indexes = [
            models.Index(fields=["title_type"]),
            models.Index(fields=["start_year"]),
        ]

    def __str__(self):
        return f"{self.primary_title} ({self.start_year})"