from datetime import timedelta
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from editorial_planning.models import EditorialFlowRun
from grid_schedule.models import PlayoutGenerationReport, ScheduleMediaItem, TvPlayout
from media_source.models import MediaCollection, MediaSource
from tv_channel.models import TvChannel
from tv_channel.services.grid_editing import compute_grid_warnings


class DashboardOverviewView(APIView):
    def get(self, request):
        now = timezone.now()
        stale_before = now - timedelta(
            days=getattr(settings, "DASHBOARD_STALE_SOURCE_DAYS", 7)
        )
        since = now - timedelta(hours=24)
        channels = list(TvChannel.objects.select_related("catalog").all())
        enabled = [c for c in channels if c.is_enabled]
        active_playouts = {
            p.tv_channel_id: p
            for p in TvPlayout.objects.filter(
                is_active=True, tv_channel__in=enabled
            ).select_related("tv_channel")
        }
        item_filter = self._playout_filter(list(active_playouts.values()))
        items = (
            list(
                ScheduleMediaItem.objects.filter(item_filter, ends_at__gt=now)
                .select_related(
                    "item",
                    "item__container",
                    "block_container_selection__tv_playout",
                    "flexible_selection__tv_playout",
                    "parent_schedule_item__block_container_selection__tv_playout",
                    "parent_schedule_item__flexible_selection__tv_playout",
                )
                .order_by("starts_at")
            )
            if active_playouts
            else []
        )
        by_channel = {c.id: [] for c in enabled}
        for item in items:
            channel_id = self._channel_id(item)
            if channel_id in by_channel:
                by_channel[channel_id].append(item)
        on_air = []
        for channel in enabled:
            timeline = by_channel[channel.id]
            current = next(
                (i for i in timeline if i.starts_at <= now < i.ends_at), None
            )
            nxt = next((i for i in timeline if i.starts_at > now), None)
            if current:
                on_air.append(
                    {
                        "tv_channel_id": channel.id,
                        "name": channel.name,
                        "logo": channel.logo.url if channel.logo else None,
                        "current": self._item(current, True),
                        "next": self._item(nxt, False) if nxt else None,
                    }
                )
        reports = list(
            PlayoutGenerationReport.objects.filter(tv_playout__tv_channel__in=channels)
            .select_related("tv_playout__tv_channel")
            .order_by("tv_playout__tv_channel_id", "-created_at", "-id")
        )
        latest = {}
        for report in reports:
            latest.setdefault(report.tv_playout.tv_channel_id, report)
        alerts = []
        for channel_id, report in latest.items():
            for issue in report.issues or []:
                if issue.get("severity") in ("error", "warning"):
                    alerts.append(
                        {
                            "severity": issue["severity"],
                            "kind": "playout_issue",
                            "object_type": "tv_channel",
                            "object_id": channel_id,
                            "object_name": report.tv_playout.tv_channel.name,
                            "message": issue.get(
                                "message", issue.get("code", "Problème de planning")
                            ),
                            "occurred_at": report.created_at,
                        }
                    )
        stale_sources = list(
            MediaSource.objects.filter(
                Q(analyzed_at__lt=stale_before) | Q(analyzed_at__isnull=True)
            )
        )
        for source in stale_sources:
            alerts.append(
                {
                    "severity": "warning",
                    "kind": "stale_source",
                    "object_type": "media_source",
                    "object_id": source.id,
                    "object_name": source.name,
                    "message": "Cette source doit être resynchronisée.",
                    "occurred_at": source.analyzed_at or now,
                }
            )
        for channel in channels:
            grid = channel.gridlayout_set.filter(is_active=True).first()
            if grid:
                for warning in compute_grid_warnings(grid):
                    alerts.append(
                        {
                            "severity": "warning",
                            "kind": "grid_warning",
                            "object_type": "tv_channel",
                            "object_id": channel.id,
                            "object_name": channel.name,
                            "message": warning,
                            "occurred_at": grid.created_at,
                        }
                    )
        alerts.sort(
            key=lambda a: (a["severity"] != "error", -a["occurred_at"].timestamp())
        )
        recent = []
        for report in [r for r in reports if r.created_at >= since]:
            errors = sum(1 for i in report.issues or [] if i.get("severity") == "error")
            recent.append(
                {
                    "kind": "playout_failed" if errors else "playout_generated",
                    "status": "error" if errors else "success",
                    "label_params": {
                        "channel": report.tv_playout.tv_channel.name,
                        "days": self._days(report),
                    },
                    "occurred_at": report.created_at,
                    "tv_channel_id": report.tv_playout.tv_channel_id,
                }
            )
        for collection in MediaCollection.objects.filter(analyzed_at__gte=since):
            recent.append(
                {
                    "kind": "collection_analyzed",
                    "status": "success",
                    "label_params": {"collection": collection.name},
                    "occurred_at": collection.analyzed_at,
                    "tv_channel_id": None,
                }
            )
        for run in EditorialFlowRun.objects.filter(
            created_at__gte=since
        ).select_related("catalog"):
            recent.append(
                {
                    "kind": "editorial_run",
                    "status": "info",
                    "label_params": {"catalog": run.catalog.name},
                    "occurred_at": run.completed_at or run.created_at,
                    "tv_channel_id": None,
                }
            )
        recent.sort(key=lambda a: a["occurred_at"], reverse=True)
        last = max((r.created_at for r in reports), default=None)
        channels_with_alerts = len(
            {a["object_id"] for a in alerts if a["object_type"] == "tv_channel"}
        )
        return Response(
            {
                "stats": {
                    "channels_total": len(channels),
                    "channels_enabled": len(enabled),
                    "channels_on_air": len(on_air),
                    "open_alerts": len(alerts),
                    "channels_with_alerts": channels_with_alerts,
                    "sources_total": MediaSource.objects.count(),
                    "sources_stale": len(stale_sources),
                    "last_generation_at": last,
                },
                "alerts": alerts[:20],
                "recent_activity": recent[:10],
                "on_air": on_air,
            }
        )

    @staticmethod
    def _playout_filter(playouts):
        return (
            Q(block_container_selection__tv_playout__in=playouts)
            | Q(flexible_selection__tv_playout__in=playouts)
            | Q(
                parent_schedule_item__block_container_selection__tv_playout__in=playouts
            )
            | Q(parent_schedule_item__flexible_selection__tv_playout__in=playouts)
        )

    @staticmethod
    def _channel_id(item):
        if item.block_container_selection_id:
            return item.block_container_selection.tv_playout.tv_channel_id
        if item.flexible_selection_id:
            return item.flexible_selection.tv_playout.tv_channel_id
        parent = item.parent_schedule_item
        return (
            parent.block_container_selection.tv_playout.tv_channel_id
            if parent.block_container_selection_id
            else parent.flexible_selection.tv_playout.tv_channel_id
        )

    @staticmethod
    def _item(item, include_end):
        value = {"title": item.item.title, "starts_at": item.starts_at}
        if include_end:
            value["ends_at"] = item.ends_at
        return value

    @staticmethod
    def _days(report):
        return (
            max(1, (report.window_end - report.window_start).days)
            if report.window_start and report.window_end
            else 1
        )
