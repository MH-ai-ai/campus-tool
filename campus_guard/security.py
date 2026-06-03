from __future__ import annotations

from typing import Any


def is_authorized(update: Any, telegram_user_id: int) -> bool:
    user = getattr(update, "effective_user", None)
    return bool(user and getattr(user, "id", None) == telegram_user_id)
