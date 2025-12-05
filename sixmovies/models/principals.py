from django.db import models
from .titles import Title
from .actors import Actor


class TitlePrincipal(models.Model):
    id = models.BigAutoField(primary_key=True)

    title = models.ForeignKey(
        Title,
        on_delete=models.CASCADE,
        related_name="principals",
        db_index=True,
    )

    actor = models.ForeignKey(
        Actor,
        on_delete=models.CASCADE,
        related_name="principal_roles",
        db_index=True,
    )

    ordering = models.IntegerField(db_index=True)
    category = models.CharField(max_length=64, db_index=True)
    job = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        db_table = "titles_principals"
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["ordering"]),
        ]


class TitlePrincipalCharacter(models.Model):
    id = models.BigAutoField(primary_key=True)

    principal = models.ForeignKey(
        TitlePrincipal,
        on_delete=models.CASCADE,
        related_name="characters",
        db_index=True,
    )

    character_name = models.CharField(max_length=512, db_index=True)

    class Meta:
        db_table = "titles_principal_characters"
        indexes = [
            models.Index(fields=["character_name"]),
        ]