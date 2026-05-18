"""Python client for ErsatzTV scripted schedule API."""

from .client import ENDPOINTS, EndpointSpec, ErsatzTVAPIError, ErsatzTVScriptedScheduleAPI, ScriptedScheduleClient
from .models import *  # noqa: F403
from .models import __all__ as _models_all

__version__ = "0.1.0"

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "ErsatzTVAPIError",
    "ErsatzTVScriptedScheduleAPI",
    "ScriptedScheduleClient",
    "__version__",
    *_models_all,
]
