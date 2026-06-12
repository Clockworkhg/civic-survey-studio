"""Analysis configuration helpers.

Utilities for auto-detecting analysis configuration from variable
dictionary metadata. These are used during the app orchestration
flow (before tabs are rendered), not inside any single tab.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.analysis_context import AnalysisContext


def auto_suggest_config_from_dict(ctx: AnalysisContext) -> None:
    """Auto-fill analysis config from variable dictionary's 'variable usage' field.

    Only fills when the user has NOT manually set target/group/explanatory.
    Behaviour is identical to the original app.py helper (P2-4).
    """
    cfg = ctx.user_analysis_config
    vdict = ctx.variable_dict_map

    if not vdict:
        return

    # Detect recommended roles from variable usage
    suggested_targets = []
    suggested_groups = []
    suggested_expls = []

    for col in ctx.columns:
        entry = vdict.get(col, {})
        detected = entry.get("detected_usage", "")
        if not detected:
            continue

        if detected == "target":
            suggested_targets.append(col)
        elif detected == "group":
            suggested_groups.append(col)
        elif detected == "predictor":
            suggested_expls.append(col)

    # Auto-fill (only when user hasn't set, and type matches)
    if suggested_targets and not cfg.get("target_variable"):
        first = suggested_targets[0]
        if first in ctx.columns:
            cfg["target_variable"] = first

    if suggested_groups and not cfg.get("group_variables"):
        # Only keep categorical/ordinal
        valid_groups = [
            v for v in suggested_groups
            if v in ctx.columns and ctx.get_type(v) in ("categorical", "ordinal")
        ]
        if valid_groups:
            cfg["group_variables"] = valid_groups[:5]

    if suggested_expls and not cfg.get("explanatory_variables"):
        # Only keep numeric/ordinal
        valid_expls = [
            v for v in suggested_expls
            if v in ctx.columns and ctx.get_type(v) in ("numeric", "ordinal")
        ]
        if valid_expls:
            cfg["explanatory_variables"] = valid_expls[:10]
