"""
Tiny logging wrapper.

Goals:
- Keep hot paths cheap (no heavy formatting when disabled).
- Centralize log policy (info/warn/error/debug).
"""
from __future__ import annotations

import os
import time
from typing import Callable, Optional

import debug_utils


_quiet = False


def set_quiet(value: bool) -> None:
    global _quiet
    _quiet = bool(value)


def is_quiet() -> bool:
    return _quiet


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def info(message: str, module: str = "App") -> None:
    if _quiet:
        return
    print(f"[{_ts()}] [{module}] {message}")


def warn(message: str, module: str = "App") -> None:
    if _quiet:
        return
    print(f"[{_ts()}] [{module}] WARNING: {message}")


def error(message: str, module: str = "App") -> None:
    # errors are always printed (even in quiet mode)
    print(f"[{_ts()}] [{module}] ERROR: {message}")


def debug(message: str, module: str = "App") -> None:
    debug_utils.debug_print(message, module)


def debug_lazy(message_func: Callable[[], str], module: str = "App") -> None:
    debug_utils.debug_print_lazy(message_func, module)

