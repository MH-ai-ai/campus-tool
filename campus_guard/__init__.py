"""Side-effect-free public API for AutoCampusNet (internal package name: campus_guard)."""

from .auth import build_auth_params, parse_drcom_response
from .models import Config, GuardState
from .security import is_authorized
from .tray import get_tray_color
from .version import APP_VERSION

__version__ = APP_VERSION

__all__ = [
    "APP_VERSION",
    "Config",
    "GuardState",
    "__version__",
    "build_auth_params",
    "get_tray_color",
    "is_authorized",
    "parse_drcom_response",
]
