from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


_bot_health_check_fn: Callable[[], Awaitable[None]] | None = None
_bot_loop: asyncio.AbstractEventLoop | None = None


def register_bot_health_check(
    loop: asyncio.AbstractEventLoop | None,
    health_check: Callable[[], Awaitable[None]],
) -> None:
    global _bot_health_check_fn, _bot_loop
    _bot_loop = loop
    _bot_health_check_fn = health_check


def trigger_bot_health_check() -> None:
    if _bot_loop and _bot_health_check_fn:
        asyncio.run_coroutine_threadsafe(_bot_health_check_fn(), _bot_loop)
