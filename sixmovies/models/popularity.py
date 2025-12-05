# sixmovies/models/popularity.py

from django.db import models


class PopularityVersion(models.Model):
    """
    Версия расчёта актёрского рейтинга.

    Храним:
    - веса w1, w2, w3;
    - глобальные параметры байесовского рейтинга (C, M);
    - timestamp, комментарий.
    """

    created_at = models.DateTimeField(auto_now_add=True)

    # веса для формулы:
    # Popularity = w_role * S(role) + w_quality * S(quality) + w_reach * S(reach)
    weight_role = models.FloatField(help_text="w1 — вес компоненты S(role)")
    weight_quality = models.FloatField(help_text="w2 — вес компоненты S(quality)")
    weight_reach = models.FloatField(help_text="w3 — вес компоненты S(reach)")

    # параметры байесовского рейтинга
    global_mean_rating = models.FloatField(
        help_text="C — средний IMDb рейтинг по базе"
    )
    min_votes_for_weight = models.IntegerField(
        help_text="M — минимальное число голосов для сглаживания рейтинга"
    )

    notes = models.TextField(blank=True)

    class Meta:
        db_table = "popularity_versions"

    def __str__(self) -> str:
        return (
            f"Version #{self.id} "
            f"(w=({self.weight_role:.2f}, {self.weight_quality:.2f}, {self.weight_reach:.2f}), "
            f"C={self.global_mean_rating:.3f}, M={self.min_votes_for_weight})"
        )