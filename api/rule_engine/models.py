from django.db import models


# Create your models here.

class Category(models.Model):
    category = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.category


class CategoryRule(models.Model):
    category = models.OneToOneField("Category", on_delete=models.CASCADE)
    rules = models.JSONField(default=list)

    def __str__(self):
        return self.category.category
