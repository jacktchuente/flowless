from django.contrib import admin

from grid_schedule.models import BlockContainerSelection
from tv_channel.models import (
    Catalog,
    EditorialLine,
    FillerPolicy,
    GridBlock,
    GridLayout,
    TvChannel,
)



class BlockContainerSelectionInline(admin.StackedInline):
    model = BlockContainerSelection
    extra = 0
    show_change_link = True


@admin.register(Catalog)
class CatalogAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "analyze_status", "number_of_channels")
    search_fields = ("name",)


@admin.register(TvChannel)
class TvChannelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "catalog", "analyze_status", "is_enabled")
    list_select_related = ("catalog",)
    search_fields = ("name", "catalog__name")


@admin.register(EditorialLine)
class EditorialLineAdmin(admin.ModelAdmin):
    list_display = ("id", "tv_channel", "start_at", "end_at", "allow_filler")
    list_select_related = ("tv_channel",)


@admin.register(GridLayout)
class GridLayoutAdmin(admin.ModelAdmin):
    list_display = ("id", "tv_channel", "mode", "post_filler_policy", "is_active", "created_at")
    list_select_related = ("tv_channel", "post_filler_policy")


@admin.register(GridBlock)
class GridBlockAdmin(admin.ModelAdmin):
    list_display = ("id", "grid_layout", "starts_at", "ends_at", "priority")
    list_select_related = ("grid_layout",)
    inlines = [BlockContainerSelectionInline]


@admin.register(FillerPolicy)
class FillerPolicyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "duration_seconds")
