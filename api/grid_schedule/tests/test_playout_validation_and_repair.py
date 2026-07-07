from datetime import timedelta

from django.test import TestCase

from grid_schedule.models import PlayoutGenerationReport, ScheduleMediaItem
from grid_schedule.services.playout_repair_service import PlayoutRepairService
from grid_schedule.services.playout_validation_service import PlayoutValidationService
from grid_schedule.services.tv_schedule_service import GenerationResult
from grid_schedule.tests.test_post_roll_filler_service import PostRollFillerFixtureMixin
from media_source.constants import MediaProgrammingRole
from tv_channel.tasks import _save_generation_report


class PlayoutValidationServiceTests(PostRollFillerFixtureMixin, TestCase):
    def setUp(self):
        self.build_fixtures()
        self.container = self._create_container(self.main_collection, "main-a")
        self.items = [
            self._create_item(self.container, f"item-{index}") for index in range(3)
        ]

    def _validate(self):
        return PlayoutValidationService(
            tv_playout=self.tv_playout,
            editorial_line=self.editorial_line,
        ).validate()

    def test_clean_timeline_has_no_issue(self):
        first = self._create_main_scheduled_item(
            self.container, self.items[0], starts_at=self.window_start
        )
        self._create_main_scheduled_item(
            self.container, self.items[1], starts_at=first.post_roll_filler_ends_at
        )

        self.assertEqual(self._validate(), [])

    def test_gap_within_editorial_day_is_a_warning(self):
        first = self._create_main_scheduled_item(
            self.container, self.items[0], starts_at=self.window_start
        )
        self._create_main_scheduled_item(
            self.container,
            self.items[1],
            starts_at=first.post_roll_filler_ends_at + timedelta(minutes=10),
        )

        issues = self._validate()

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["code"], "gap")
        self.assertEqual(issues[0]["severity"], "warning")

    def test_gap_outside_editorial_day_is_info(self):
        # Journee editoriale 6:00-22:00; trou entre 22:20 et 23:20.
        late_start = self.window_start.replace(hour=21, minute=0)
        first = self._create_main_scheduled_item(
            self.container, self.items[0], starts_at=late_start, filler_seconds=0
        )
        # duree 3000s -> fin 21:50; trou 21:50->23:20 intersecte 6-22 => warning.
        # Pour un trou entierement hors journee, on place le premier item
        # finissant a 22:00 pile.
        first.ends_at = self.window_start.replace(hour=22, minute=0)
        first.post_roll_filler_ends_at = None
        first.save(update_fields=["ends_at", "post_roll_filler_ends_at"])
        self._create_main_scheduled_item(
            self.container,
            self.items[1],
            starts_at=self.window_start.replace(hour=23, minute=20),
        )

        issues = self._validate()

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["code"], "gap")
        self.assertEqual(issues[0]["severity"], "info")

    def test_overlap_is_an_error(self):
        first = self._create_main_scheduled_item(
            self.container, self.items[0], starts_at=self.window_start
        )
        self._create_main_scheduled_item(
            self.container,
            self.items[1],
            starts_at=first.post_roll_filler_ends_at - timedelta(seconds=60),
        )

        issues = self._validate()

        self.assertEqual([issue["code"] for issue in issues], ["overlap"])
        self.assertEqual(issues[0]["severity"], "error")

    def test_child_inside_window_is_not_an_overlap(self):
        first = self._create_main_scheduled_item(
            self.container, self.items[0], starts_at=self.window_start
        )
        self._create_main_scheduled_item(
            self.container, self.items[1], starts_at=first.post_roll_filler_ends_at
        )
        ScheduleMediaItem.objects.create(
            starts_at=first.ends_at,
            ends_at=first.ends_at + timedelta(seconds=60),
            item=self.items[2],
            role=MediaProgrammingRole.FILLER,
            parent_schedule_item=first,
        )

        self.assertEqual(self._validate(), [])

    def test_child_exceeding_parent_window_is_flagged(self):
        first = self._create_main_scheduled_item(
            self.container, self.items[0], starts_at=self.window_start
        )
        ScheduleMediaItem.objects.create(
            starts_at=first.ends_at,
            ends_at=first.post_roll_filler_ends_at + timedelta(seconds=60),
            item=self.items[2],
            role=MediaProgrammingRole.FILLER,
            parent_schedule_item=first,
        )

        issues = self._validate()

        self.assertIn("child_outside_window", [issue["code"] for issue in issues])


class PlayoutRepairServiceTests(PostRollFillerFixtureMixin, TestCase):
    def setUp(self):
        self.build_fixtures()
        self.container = self._create_container(self.main_collection, "main-a")
        self.items = [
            self._create_item(self.container, f"item-{index}") for index in range(3)
        ]

    def _repair(self):
        return PlayoutRepairService(
            tv_playout=self.tv_playout,
            editorial_line=self.editorial_line,
            window_start=self.window_start,
            window_end=self.window_end,
        ).repair()

    def _validate(self):
        return PlayoutValidationService(
            tv_playout=self.tv_playout,
            editorial_line=self.editorial_line,
        ).validate()

    def test_overlapping_post_roll_window_is_trimmed(self):
        first = self._create_main_scheduled_item(
            self.container, self.items[0], starts_at=self.window_start
        )
        second_start = first.post_roll_filler_ends_at - timedelta(seconds=60)
        self._create_main_scheduled_item(
            self.container, self.items[1], starts_at=second_start
        )
        child = ScheduleMediaItem.objects.create(
            starts_at=first.ends_at,
            ends_at=first.post_roll_filler_ends_at,
            item=self.items[2],
            role=MediaProgrammingRole.FILLER,
            parent_schedule_item=first,
        )

        result = self._repair()

        first.refresh_from_db()
        child.refresh_from_db()
        self.assertEqual(result.trimmed_overlaps, 1)
        self.assertEqual(first.post_roll_filler_ends_at, second_start)
        self.assertEqual(child.ends_at, second_start)
        self.assertFalse(any(issue["code"] == "overlap" for issue in self._validate()))

    def test_gap_is_backfilled_with_fillers(self):
        first = self._create_main_scheduled_item(
            self.container, self.items[0], starts_at=self.window_start
        )
        gap_start = first.post_roll_filler_ends_at
        self._create_main_scheduled_item(
            self.container, self.items[1], starts_at=gap_start + timedelta(minutes=10)
        )

        filler_collection = self._create_collection("Fillers", role=MediaProgrammingRole.FILLER)
        filler_container = self._create_container(filler_collection, "filler-folder")
        for index in range(12):
            self._create_item(filler_container, f"filler-{index}", duration_seconds=60)

        result = self._repair()

        self.assertEqual(result.repaired_gaps, 1)
        children = ScheduleMediaItem.objects.filter(
            parent_schedule_item=first, starts_at__gte=gap_start
        )
        self.assertGreater(children.count(), 0)
        self.assertFalse(any(issue["code"] == "gap" for issue in self._validate()))

    def test_huge_gap_is_left_alone(self):
        first = self._create_main_scheduled_item(
            self.container, self.items[0], starts_at=self.window_start
        )
        self._create_main_scheduled_item(
            self.container,
            self.items[1],
            starts_at=first.post_roll_filler_ends_at + timedelta(hours=2),
        )
        filler_collection = self._create_collection("Fillers", role=MediaProgrammingRole.FILLER)
        filler_container = self._create_container(filler_collection, "filler-folder")
        self._create_item(filler_container, "filler-0", duration_seconds=60)

        result = self._repair()

        self.assertEqual(result.repaired_gaps, 0)
        self.assertTrue(any(issue["code"] == "gap" for issue in self._validate()))


class GenerationReportPersistenceTests(PostRollFillerFixtureMixin, TestCase):
    def setUp(self):
        self.build_fixtures()

    def test_report_is_persisted_from_a_generation_result(self):
        result = GenerationResult(
            tv_playout=self.tv_playout,
            created=True,
            generated_items=4,
            warnings=["Block x generated 0 item(s), minimum expected is 1."],
            filled_items=2,
            repaired_gaps=1,
            trimmed_overlaps=0,
            issues=[
                {
                    "code": "gap",
                    "severity": "warning",
                    "message": "Gap of 600s before scheduled item 12.",
                    "schedule_item_id": 12,
                    "starts_at": None,
                    "ends_at": None,
                }
            ],
            window_start=self.window_start,
            window_end=self.window_end,
        )

        _save_generation_report(self.tv_channel, trigger="generate", result=result)

        report = PlayoutGenerationReport.objects.get(tv_playout=self.tv_playout)
        self.assertEqual(report.generated_items, 4)
        self.assertEqual(report.filled_items, 2)
        self.assertEqual(report.repaired_gaps, 1)
        self.assertEqual(len(report.issues), 2)
        codes = {issue["code"] for issue in report.issues}
        self.assertEqual(codes, {"generation", "gap"})

    def test_error_report_targets_the_active_playout(self):
        _save_generation_report(
            self.tv_channel, trigger="extend", error=RuntimeError("boom")
        )

        report = PlayoutGenerationReport.objects.get(tv_playout=self.tv_playout)
        self.assertEqual(report.trigger, "extend")
        self.assertEqual(report.issues[0]["code"], "generation_failed")
        self.assertEqual(report.issues[0]["severity"], "error")
