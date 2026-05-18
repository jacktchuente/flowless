from django.contrib import admin

from grid_layout_preset.models import GridBlockPreset, GridLayoutPreset



@admin.register(GridLayoutPreset)
class GridLayoutPresetAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(GridBlockPreset)
class GridBlockPresetAdmin(admin.ModelAdmin):
    list_display = ("id", "grid_layout", "starts_at", "ends_at", "priority")
    list_select_related = ("grid_layout",)
    search_fields = ("grid_layout__name",)
