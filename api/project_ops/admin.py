from django.contrib import admin

from rule_engine.models import Category, CategoryRule

# Register your models here.
for element in [Category, CategoryRule]:
    admin.site.register(element)
