"""Side-effect-free public API for Campus Guard."""

from .auth import build_auth_params, parse_drcom_response
from .models import Config, GuardState
from .security import is_authorized
from .tray import get_tray_color

__all__ = [
    "Config",
    "GuardState",
    "build_auth_params",
    "get_tray_color",
    "is_authorized",
    "parse_drcom_response",
]
