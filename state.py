"""
Lightweight state containers (Phase 2).

These do not replace config.py yet; they exist to reduce implicit coupling
in a few hot paths without changing behavior.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BotState:
    running: bool
    is_looting: bool


@dataclass
class VisionState:
    connected_window: object
    calibrator: object


@dataclass
class CombatState:
    auto_attack_enabled: bool
    assist_only_enabled: bool

