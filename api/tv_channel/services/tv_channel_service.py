from rule_engine.services.tv_channel_editorial_line_generator.tv_channel_editorial_line_generator_with_llm import \
    TvChannelEditorialLineGeneratorWithLlm
from rule_engine.services.tv_channel_grid_generator.tv_channel_grid_generator_with_preset_and_llm import \
    TvChannelGridGeneratorWithPresetAndLlm
from rule_engine.services.tv_channel_grid_generator.tv_channel_grid_generator_with_llm import \
    TvChannelGridGeneratorWithLlm, TvChannelGridGeneratorWithLlmPayload
from rule_engine.services.tv_channel_grid_generator.tv_channel_grid_generator_with_randomness import \
    TvChannelGridGeneratorPayload, TvChannelGridGeneratorWithRandomness
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db import transaction

from grid_schedule.models import TvPlayout
from media_source.constants import MediaContainerKind
from tv_channel.models import (
    ChannelProgrammingMode,
    EditorialLine,
    FillerPolicy,
    GridBlock,
    GridLayout,
    GridLayoutMode,
    MarathonConfig,
    MarathonKindPolicy,
    TvChannel,
)


class TvChannelService:
    GRID_GENERATION_MODE_FULL_LLM = "full_llm"
    GRID_GENERATION_MODE_PRESET_AND_LLM = "preset_and_llm"
    GRID_GENERATION_MODE_RANDOM = "random"
    GRID_GENERATION_MODES = {
        GRID_GENERATION_MODE_FULL_LLM,
        GRID_GENERATION_MODE_PRESET_AND_LLM,
        GRID_GENERATION_MODE_RANDOM,
    }

    # Rotation par defaut d'une chaine marathon: 2 episodes de serie a la
    # suite, films a l'unite, autres kinds exclus tant qu'ils n'ont pas de
    # policy. Quotas egaux pour alterner les runs (serie x2 -> film x1).
    DEFAULT_MARATHON_POLICIES = (
        {"container_kind": MediaContainerKind.SERIES, "min_run": 2, "max_run": 2, "quota": 1},
        {"container_kind": MediaContainerKind.STANDALONE_VIDEO, "min_run": 1, "max_run": 1, "quota": 1},
    )

    def __init__(self, tv_channel: TvChannel):
        self.tv_channel = tv_channel

    def generate_editorial_line_and_grid(
        self,
        reboot=False,
        grid_generation_mode: str = GRID_GENERATION_MODE_FULL_LLM,
        regenerate_editorial_line: bool = False,
    ):
        if grid_generation_mode not in self.GRID_GENERATION_MODES:
            raise ValidationError("Invalid grid_generation_mode.")

        editorial_line = self._get_or_generate_editorial_line(
            regenerate_editorial_line=regenerate_editorial_line,
        )

        if self.tv_channel.programming_mode == ChannelProgrammingMode.MARATHON:
            # Pas de blocs en marathon: grid_generation_mode est ignore, la
            # grille porte la config de rotation.
            grid_layout = self._create_active_marathon_grid_layout(editorial_line, reboot=reboot)
            return {
                "tv_channel": self.tv_channel,
                "editorial_line": editorial_line,
                "grid_layout": grid_layout,
                "blocks": [],
            }

        grid_payload = {
            "name": self.tv_channel.name,
            "description": self.tv_channel.description or "",
            "specification": self.tv_channel.specification or "",
            "start_at": editorial_line.start_at,
            "end_at": editorial_line.end_at,
            "allow_filler": editorial_line.allow_filler,
            "allowed": editorial_line.allowed,
            "preferred": editorial_line.preferred,
            "forbidden": editorial_line.forbidden,
        }
        if grid_generation_mode == self.GRID_GENERATION_MODE_FULL_LLM:
            grid_service = TvChannelGridGeneratorWithLlm(tv_channel_data=TvChannelGridGeneratorWithLlmPayload(**grid_payload))
        elif grid_generation_mode == self.GRID_GENERATION_MODE_PRESET_AND_LLM:
            grid_service = TvChannelGridGeneratorWithPresetAndLlm(
                tv_channel_data=TvChannelGridGeneratorPayload(**grid_payload)
            )
        else:
            grid_service = TvChannelGridGeneratorWithRandomness(
                tv_channel_data=TvChannelGridGeneratorPayload(**grid_payload)
            )
        blocks = grid_service.get_blocks()
        grid_layout = self._create_active_grid_layout(blocks, reboot=reboot)
        return {
            "tv_channel": self.tv_channel,
            "editorial_line": editorial_line,
            "grid_layout": grid_layout,
            "blocks": blocks,
        }

    def _get_or_generate_editorial_line(self, *, regenerate_editorial_line: bool) -> EditorialLine:
        editorial_line = self._get_existing_editorial_line()
        if editorial_line is not None and not regenerate_editorial_line:
            return editorial_line

        editorial_service = TvChannelEditorialLineGeneratorWithLlm(
            tv_channel_data={
                "name": self.tv_channel.name,
                "description": self.tv_channel.description or "",
                "specification": self.tv_channel.specification or "",
            }
        )
        editorial_data = editorial_service.get_editorial_line()
        return self._upsert_editorial_line(editorial_data)

    def _upsert_editorial_line(self, editorial_data) -> EditorialLine:
        editorial_line, _ = EditorialLine.objects.get_or_create(tv_channel=self.tv_channel)
        for field, value in editorial_data.items():
            setattr(editorial_line, field, value)
        editorial_line.save()
        return editorial_line

    def _create_active_marathon_grid_layout(self, editorial_line: EditorialLine, *, reboot: bool) -> GridLayout:
        with transaction.atomic():
            # Une regeneration de blueprint ne doit pas perdre la rotation
            # personnalisee: la config du layout marathon precedent est clonee.
            previous_policies = list(
                MarathonKindPolicy.objects.filter(
                    config__grid_layout__tv_channel=self.tv_channel,
                    config__grid_layout__is_active=True,
                    config__grid_layout__mode=GridLayoutMode.MARATHON,
                ).values("container_kind", "min_run", "max_run", "quota")
            )
            self._deactivate_active_layouts_and_playouts(reboot=reboot)
            post_filler_policy = None
            if editorial_line.allow_filler:
                post_filler_policy = FillerPolicy.objects.get_or_create_for_params()
            grid_layout = GridLayout.objects.create(
                tv_channel=self.tv_channel,
                is_active=True,
                mode=GridLayoutMode.MARATHON,
                post_filler_policy=post_filler_policy,
            )
            config = MarathonConfig.objects.create(grid_layout=grid_layout)
            policies = previous_policies or [dict(policy) for policy in self.DEFAULT_MARATHON_POLICIES]
            MarathonKindPolicy.objects.bulk_create(
                [MarathonKindPolicy(config=config, **policy) for policy in policies]
            )
        return grid_layout

    def _deactivate_active_layouts_and_playouts(self, *, reboot: bool) -> None:
        active_layouts = GridLayout.objects.filter(
            tv_channel=self.tv_channel,
            is_active=True,
        )
        if reboot or active_layouts.exists():
            active_layouts.update(is_active=False)
        TvPlayout.objects.filter(
            tv_channel=self.tv_channel,
            is_active=True,
        ).update(is_active=False)

    def _create_active_grid_layout(self, blocks, *, reboot: bool) -> GridLayout:
        with transaction.atomic():
            self._deactivate_active_layouts_and_playouts(reboot=reboot)

            grid_layout = GridLayout.objects.create(
                tv_channel=self.tv_channel,
                is_active=True,
            )
            created_blocks = GridBlock.objects.bulk_create(
                [
                    GridBlock(
                        grid_layout=grid_layout,
                        starts_at=block.starts_at,
                        ends_at=block.ends_at,
                        priority=block.priority,
                        min_items=block.min_items,
                        max_items=block.max_items,
                        min_duration_seconds_per_item=block.min_duration_seconds_per_item,
                        max_duration_seconds_per_item=block.max_duration_seconds_per_item,
                        allowed=block.allowed,
                        preferred=block.preferred,
                        forbidden=block.forbidden,
                    )
                    for block in blocks
                ]
            )
            editorial_line = self._get_existing_editorial_line()
            if editorial_line is None:
                raise ValidationError("TvChannel must have an editorial line before creating a grid.")

            if editorial_line.allow_filler:
                self._attach_default_post_filler_policies(created_blocks)
        return grid_layout

    def _attach_default_post_filler_policies(self, blocks: list[GridBlock]) -> None:
        filler_policy = FillerPolicy.objects.get_or_create_for_params()
        for block in blocks:
            block.post_filler_policy = filler_policy

        GridBlock.objects.bulk_update(blocks, ["post_filler_policy"])

    def _get_existing_editorial_line(self) -> EditorialLine | None:
        try:
            return self.tv_channel.editorialline
        except ObjectDoesNotExist:
            return None
