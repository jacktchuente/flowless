from django.core.exceptions import ValidationError

from media_source.constants import MediaContainerKind, MediaNature
from media_source.data import categories
from tv_channel.models import GridLayout, GridLayoutMode


class GridNotEditableError(ValueError):
    pass


def get_editable_grid_layout(tv_channel) -> GridLayout:
    layout = tv_channel.gridlayout_set.filter(is_active=True).order_by("-created_at", "-id").first()
    if layout is None:
        raise GridNotEditableError("Channel has no active grid.")
    if layout.mode == GridLayoutMode.FLEXIBLE:
        raise GridNotEditableError("Flexible grid editing is not supported yet.")
    return layout


def ensure_block_is_editable(block) -> None:
    try:
        active_layout = get_editable_grid_layout(block.grid_layout.tv_channel)
    except GridNotEditableError:
        raise
    if active_layout.pk != block.grid_layout_id:
        raise GridNotEditableError("Only blocks in the active grid can be edited.")


def _minutes(value):
    return value.hour * 60 + value.minute


def compute_grid_warnings(grid_layout) -> list[str]:
    blocks = list(grid_layout.gridblock_set.all().order_by("starts_at", "id"))
    warnings = []
    for previous, current in zip(blocks, blocks[1:]):
        previous_end = _minutes(previous.ends_at)
        current_start = _minutes(current.starts_at)
        if previous_end < current_start:
            warnings.append(
                f"Gap between blocks {previous.id} and {current.id} "
                f"({previous.ends_at:%H:%M}-{current.starts_at:%H:%M})."
            )
        elif previous_end > current_start:
            warnings.append(
                f"Overlap between blocks {previous.id} and {current.id} "
                f"({current.starts_at:%H:%M}-{previous.ends_at:%H:%M})."
            )

    editorial_line = getattr(grid_layout.tv_channel, "editorialline", None)
    if blocks and editorial_line is not None:
        if blocks[0].starts_at > editorial_line.start_at:
            warnings.append("The first block starts after the editorial window.")
        if blocks[-1].ends_at < editorial_line.end_at:
            warnings.append("The last block ends before the editorial window.")

    complete_values = {
        "categories": set(categories),
        "natures": {choice.value for choice in MediaNature},
        "container_kinds": {choice.value for choice in MediaContainerKind},
    }
    for block in blocks:
        for axis, vocabulary in complete_values.items():
            if not getattr(block, f"allowed_{axis}") and set(getattr(block, f"forbidden_{axis}")) >= vocabulary:
                warnings.append(f"Block {block.id} forbids every {axis.replace('_', ' ')} value.")
    return warnings
