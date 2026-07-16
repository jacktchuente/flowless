from django.contrib import admin

from rule_engine.models import Category, CategoryNature, CategoryRule


class CategoryNatureInline(admin.TabularInline):
    model = CategoryNature
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    inlines = [CategoryNatureInline]


admin.site.register(CategoryRule)
