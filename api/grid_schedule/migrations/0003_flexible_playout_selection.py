# Generated manually for flexible playout scheduling.

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("editorial_planning", "0001_initial"),
        ("grid_schedule", "0002_alter_tvplayout_grid"),
        ("media_source", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FlexiblePlayoutSelection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField(default=0)),
                ("path_position", models.PositiveIntegerField()),
                ("planned_item_count", models.PositiveIntegerField(default=1)),
                (
                    "status",
                    models.IntegerField(
                        choices=[
                            (0, "pending"),
                            (1, "started"),
                            (2, "paused"),
                            (3, "completed"),
                            (4, "cancelled"),
                            (5, "skipped"),
                        ],
                        default=0,
                    ),
                ),
                (
                    "last_scheduled_item",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="media_source.mediaitem",
                    ),
                ),
                (
                    "media_container",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="media_source.mediacontainer"),
                ),
                (
                    "segment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="flexible_playout_selections",
                        to="editorial_planning.editorialsegment",
                    ),
                ),
                (
                    "tv_playout",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="flexible_selections",
                        to="grid_schedule.tvplayout",
                    ),
                ),
            ],
        ),
        migrations.AlterField(
            model_name="schedulemediaitem",
            name="block_container_selection",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="grid_schedule.blockcontainerselection",
            ),
        ),
        migrations.AddField(
            model_name="schedulemediaitem",
            name="flexible_selection",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="grid_schedule.flexibleplayoutselection",
            ),
        ),
        migrations.AddConstraint(
            model_name="flexibleplayoutselection",
            constraint=models.UniqueConstraint(
                fields=("tv_playout", "order"),
                name="unique_flexible_selection_order_per_playout",
            ),
        ),
        migrations.AddIndex(
            model_name="flexibleplayoutselection",
            index=models.Index(fields=["tv_playout", "status"], name="grid_schedu_tv_play_9e889e_idx"),
        ),
        migrations.AddIndex(
            model_name="flexibleplayoutselection",
            index=models.Index(fields=["segment", "status"], name="grid_schedu_segment_55c4e6_idx"),
        ),
        migrations.AddConstraint(
            model_name="schedulemediaitem",
            constraint=models.CheckConstraint(
                check=(
                    Q(block_container_selection__isnull=False, flexible_selection__isnull=True)
                    | Q(block_container_selection__isnull=True, flexible_selection__isnull=False)
                ),
                name="schedule_item_has_exactly_one_selection",
            ),
        ),
    ]
