# Copyright (c) 2026 Adrien40
# This file is part of Flipr Local.
"""Identify the Flipr model from its Bluetooth name (pure function)."""

from __future__ import annotations


def get_flipr_model(name: str | None) -> str:
    if not name:
        return "Flipr"
    name_upper = name.upper()
    if name_upper.startswith("F3"):
        return "Flipr AnalysR 3"
    if name_upper.startswith("F2"):
        return "Flipr AnalysR"
    if name_upper.startswith(("FLIPR 01", "FLIPR 00")):
        return "Flipr Start Max"
    return "Flipr"
