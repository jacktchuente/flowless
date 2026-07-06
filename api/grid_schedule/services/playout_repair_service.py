import logging
from dataclasses import dataclass
from datetime import datetime

from grid_schedule.models import ScheduleMediaItem, TvPlayout
from grid_schedule.services.playout_validation_service import (
    GAP_THRESHOLD_SECONDS,
    load_playout_timeline,
    occupied_end,
)
from grid_schedule.services.post_roll_filler_service import PostRollFillerService

logger = logging.getLogger(__name__)

MIN_CHILD_DURATION_SECONDS = 10
# Au-dela, le trou est un choix de grille (entre blocs, nuit...): on ne le
# comble pas de fillers, il reste signale et absorbe par le pad ErsatzTV.
MAX_BACKFILL_SECONDS = 1800


@dataclass
class RepairResult:
    repaired_gaps: int = 0
    trimmed_overlaps: int = 0


class PlayoutRepairService:
    """Reparation automatique apres generation.

    - Chevauchements: la fenetre post-roll (et ses enfants) du precedent est
      tronquee au debut de l'item suivant. Un chevauchement entre deux items
      MAIN eux-memes n'est pas repare (bug de generation, reste en erreur).
    - Trous: backfill avec des fillers rattaches a l'item precedent; le
      residuel non comble reste couvert par le pad ErsatzTV.
    """

    def __init__(self, *, tv_playout: TvPlayout, editorial_line, window_start: datetime, window_end: datetime):
        self.tv_playout = tv_playout
        self.editorial_line = editorial_line
        self.window_start = window_start
        self.window_end = window_end

    def repair(self) -> RepairResult:
        result = RepairResult()
        main_items, children_by_parent = load_playout_timeline(self.tv_playout)
        if not main_items:
            return result

        self._trim_overlaps(main_items, children_by_parent, result)

        if self.editorial_line is not None and self.editorial_line.allow_filler:
            self._backfill_gaps(main_items, children_by_parent, result)

        return result

    def _trim_overlaps(self, main_items, children_by_parent, result: RepairResult) -> None:
        for previous, current in zip(main_items, main_items[1:]):
            children = children_by_parent.get(previous.id, [])
            previous_occupied = occupied_end(previous, children)
            if current.starts_at >= previous_occupied:
                continue
            if previous.ends_at > current.starts_at:
                # Chevauchement des contenus principaux: non reparable ici.
                continue

            trimmed = False
            kept_children = []
            for child in children:
                if child.starts_at >= current.starts_at:
                    child.delete()
                    trimmed = True
                    continue
                if child.ends_at > current.starts_at:
                    child.ends_at = current.starts_at
                    if (child.ends_at - child.starts_at).total_seconds() < MIN_CHILD_DURATION_SECONDS:
                        child.delete()
                    else:
                        child.save(update_fields=["ends_at"])
                        kept_children.append(child)
                    trimmed = True
                    continue
                kept_children.append(child)
            children_by_parent[previous.id] = kept_children

            if previous.post_roll_filler_ends_at and previous.post_roll_filler_ends_at > current.starts_at:
                previous.post_roll_filler_ends_at = current.starts_at
                previous.save(update_fields=["post_roll_filler_ends_at"])
                trimmed = True

            if trimmed:
                result.trimmed_overlaps += 1
                logger.info(
                    "PlayoutRepairService trimmed overlap playout_id=%s previous_id=%s next_id=%s",
                    self.tv_playout.id,
                    previous.id,
                    current.id,
                )

    def _backfill_gaps(self, main_items, children_by_parent, result: RepairResult) -> None:
        filler_service = PostRollFillerService(
            tv_playout=self.tv_playout,
            window_start=self.window_start,
            window_end=self.window_end,
        )
        for previous, current in zip(main_items, main_items[1:]):
            if previous.starts_at < self.window_start:
                continue
            children = children_by_parent.get(previous.id, [])
            gap_start = occupied_end(previous, children)
            gap_seconds = int((current.starts_at - gap_start).total_seconds())
            if gap_seconds <= GAP_THRESHOLD_SECONDS or gap_seconds > MAX_BACKFILL_SECONDS:
                continue
            created = filler_service.fill_gap(
                parent_item=previous,
                gap_start=gap_start,
                gap_end=current.starts_at,
            )
            if created <= 0:
                continue
            # La fenetre reservee couvre desormais le trou: le residuel non
            # comble reste absorbe par le pad ErsatzTV.
            previous.post_roll_filler_ends_at = current.starts_at
            previous.save(update_fields=["post_roll_filler_ends_at"])
            result.repaired_gaps += 1
            logger.info(
                "PlayoutRepairService backfilled gap playout_id=%s after_item_id=%s seconds=%s created=%s",
                self.tv_playout.id,
                previous.id,
                gap_seconds,
                created,
            )
