from django.contrib import admin

from grid_schedule.models import BlockContainerSelection, FlexiblePlayoutSelection, ScheduleMediaItem, TvPlayout


class ScheduleMediaItemInline(admin.StackedInline):
    model = ScheduleMediaItem
    fk_name = "block_container_selection"
    extra = 0
    show_change_link = True


class FlexibleScheduleMediaItemInline(admin.StackedInline):
    model = ScheduleMediaItem
    fk_name = "flexible_selection"
    extra = 0
    show_change_link = True


@admin.register(TvPlayout)
class TvPlayoutAdmin(admin.ModelAdmin):
    list_display = ("id", "tv_channel", "grid", "is_active", "created_at")
    list_select_related = ("tv_channel", "grid")
    search_fields = ("tv_channel__name",)


@admin.register(BlockContainerSelection)
class BlockContainerSelectionAdmin(admin.ModelAdmin):
    list_display = ("id", "tv_playout", "block", "media_container", "order", "status")
    list_select_related = ("tv_playout", "block", "media_container")
    inlines = [ScheduleMediaItemInline]


@admin.register(FlexiblePlayoutSelection)
class FlexiblePlayoutSelectionAdmin(admin.ModelAdmin):
    list_display = ("id", "tv_playout", "segment", "media_container", "path_position", "order", "status")
    list_select_related = ("tv_playout", "segment", "media_container")
    inlines = [FlexibleScheduleMediaItemInline]


@admin.register(ScheduleMediaItem)
class ScheduleMediaItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "item",
        "block_container_selection",
        "flexible_selection",
        "starts_at",
        "ends_at",
        "added_to_playout",
    )
    list_select_related = ("item", "block_container_selection", "flexible_selection")
