from django.db import models

from media_source.constants import MediaNature


# Create your models here.

class Category(models.Model):
    category = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.category


class CategoryNature(models.Model):
    category = models.ForeignKey("Category", on_delete=models.CASCADE, related_name="nature_links")
    # Convention : une categorie sans aucun lien est valable pour toutes les natures.
    nature = models.IntegerField(choices=MediaNature.choices)

    class Meta:
        unique_together = ("category", "nature")

    def __str__(self):
        return f"{self.category.category} -> {self.get_nature_display()}"


class CategoryRule(models.Model):
    category = models.OneToOneField("Category", on_delete=models.CASCADE)
    rules = models.JSONField(default=list)

    def __str__(self):
        return self.category.category


class VocabularyEntry(models.Model):
    """
    Vocabulaire des axes de regles editoriales a valeurs ouvertes
    (directors, actors, studios, countries, langues...). Alimente a la sync
    des collections, purge des orphelins par tache periodique.
    """
    axis = models.CharField(max_length=32)
    value = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["axis", "value"], name="unique_vocabulary_axis_value"),
        ]
        indexes = [
            models.Index(fields=["axis", "value"]),
        ]

    def __str__(self):
        return f"{self.axis}: {self.value}"
