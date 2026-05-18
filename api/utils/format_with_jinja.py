from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def format_with_jinja(
        template_path: str | Path,
        context: Mapping[str, Any] | None = None,
) -> str:
    template_path = Path(template_path)
    environment = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )
    template = environment.get_template(template_path.name)
    return template.render(**(context or {}))
