from tv_channel.models import GridBlock
from grid_schedule.services.tv_schedule_matching_service import TvScheduleMatchingService


class GridBlockService:

    def __init__(self, grid_block: GridBlock):
        self.grid_block = grid_block

    def get_available_media_count(self) -> int:
        tv_channel = self.grid_block.grid_layout.tv_channel
        matching_service = TvScheduleMatchingService(tv_channel=tv_channel)
        stats = matching_service.get_block_match_stats(self.grid_block)
        return stats["matching_media_item_count"]
