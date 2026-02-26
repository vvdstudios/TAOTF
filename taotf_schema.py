"""
TAOTF Schema — Single source of truth for taxonomy, normalization, and validation.

By Vivid Studio (https://vividstudio.me)
"""
from __future__ import annotations

from typing import Any

# ── Canonical sets ────────────────────────────────────────────────────────────

VALID_PILLARS = frozenset({
    "Health & Longevity",
    "Home & Living",
    "Education & Knowledge",
    "Energy & Sustainability",
    "Space & Exploration",
    "Nation & Society",
    "Environment & Planet",
    "Human Connection",
    "Digital Identity",
    "Human-AI Collaboration",
})

VALID_SIGNAL_TYPES = frozenset({
    "protective_aspiration",
    "access_aspiration",
    "transformation_aspiration",
    "connection_aspiration",
    "self_directed_aspiration",
})

VALID_BENEFICIARIES = frozenset({
    "self",
    "family",
    "community",
    "humanity",
    "unknown",
})

VALID_VALENCES = frozenset({
    "hope",
    "longing",
    "urgency",
    "gratitude",
    "grief",
    "joy",
    "neutral",
})

VALID_TIME_HORIZONS = frozenset({
    "immediate",
    "near_term",
    "long_term",
    "unspecified",
})

# ── Normalization maps ────────────────────────────────────────────────────────
# Maps observed non-canonical values → canonical values.
# Built from analysis of 2,269 signals showing 38 unique pillar names.

PILLAR_NORMALIZATION: dict[str, str] = {
    # Economy variants → Nation & Society
    "Economy & Prosperity": "Nation & Society",
    "Economy & Wealth": "Nation & Society",
    "Economic Prosperity": "Nation & Society",
    "Economy & Society": "Nation & Society",
    "Economy & Innovation": "Nation & Society",
    "Finance & Economy": "Nation & Society",
    # Family variants → Home & Living
    "Family & Living": "Home & Living",
    "Family & Relationships": "Home & Living",
    "Family": "Home & Living",
    "Family & Society": "Home & Living",
    "Work & Life Balance": "Home & Living",
    # Self-development variants → Education & Knowledge
    "Self-Development": "Education & Knowledge",
    "Self-Directed": "Education & Knowledge",
    "Self-Directed Aspiration": "Education & Knowledge",
    # Signal types that leaked into pillar field
    "self_directed_aspiration": "Education & Knowledge",
    "access_aspiration": "Education & Knowledge",
    # Spirituality → Human Connection
    "Spirituality": "Human Connection",
    "Spirituality & Beliefs": "Human Connection",
    "spirituality": "Human Connection",
    # Transportation → Space & Exploration
    "Transportation": "Space & Exploration",
    "Mobility & Transportation": "Space & Exploration",
    "Travel & Adventure": "Space & Exploration",
    # Arts & culture → Human Connection
    "Culture & Arts": "Human Connection",
    "Entertainment & Arts": "Human Connection",
    "Entertainment & Leisure": "Human Connection",
    # Misc
    "Transformation & Aspiration": "Human Connection",
    "Humanity": "Nation & Society",
    "unknown": "Nation & Society",
}

SIGNAL_TYPE_NORMALIZATION: dict[str, str] = {
    "community_aspiration": "connection_aspiration",
    "hope_aspiration": "self_directed_aspiration",
    "neutral": "self_directed_aspiration",
    "unknown": "self_directed_aspiration",
}

BENEFICIARY_NORMALIZATION: dict[str, str] = {}  # All observed values are canonical

VALENCE_NORMALIZATION: dict[str, str] = {}  # All observed values are canonical

TIME_HORIZON_NORMALIZATION: dict[str, str] = {}  # All observed values are canonical


# ── Functions ─────────────────────────────────────────────────────────────────

def normalize_pillar(value: str | None) -> str:
    """Normalize a pillar name to canonical form."""
    if not value:
        return "Nation & Society"
    return PILLAR_NORMALIZATION.get(value, value)


def normalize_signal_type(value: str | None) -> str:
    """Normalize a signal type to canonical form."""
    if not value:
        return "self_directed_aspiration"
    return SIGNAL_TYPE_NORMALIZATION.get(value, value)


def normalize_beneficiary(value: str | None) -> str:
    """Normalize a beneficiary to canonical form."""
    if not value:
        return "unknown"
    return BENEFICIARY_NORMALIZATION.get(value, value)


def normalize_valence(value: str | None) -> str:
    """Normalize an emotional valence to canonical form."""
    if not value:
        return "neutral"
    return VALENCE_NORMALIZATION.get(value, value)


def normalize_time_horizon(value: str | None) -> str:
    """Normalize a time horizon to canonical form."""
    if not value:
        return "unspecified"
    return TIME_HORIZON_NORMALIZATION.get(value, value)


def normalize_signal(signal: dict[str, Any]) -> dict[str, Any]:
    """Normalize all taxonomy fields in a signal to canonical values. Returns a new dict."""
    out = dict(signal)
    if out.get("quality") != "valid":
        return out
    out["primary_pillar"] = normalize_pillar(out.get("primary_pillar"))
    out["signal_type"] = normalize_signal_type(out.get("signal_type"))
    out["beneficiary"] = normalize_beneficiary(out.get("beneficiary"))
    out["emotional_valence"] = normalize_valence(out.get("emotional_valence"))
    out["time_horizon"] = normalize_time_horizon(out.get("time_horizon"))
    # Normalize secondary pillars too
    if "secondary_pillars" in out and isinstance(out["secondary_pillars"], list):
        out["secondary_pillars"] = [normalize_pillar(p) for p in out["secondary_pillars"]]
    return out


def validate_signal(signal: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a signal against the canonical schema. Returns (is_valid, list_of_issues)."""
    issues: list[str] = []
    if signal.get("quality") != "valid":
        return True, issues  # Non-valid signals don't need taxonomy validation

    pillar = signal.get("primary_pillar")
    if pillar and pillar not in VALID_PILLARS:
        issues.append(f"primary_pillar '{pillar}' not in canonical set")

    sig_type = signal.get("signal_type")
    if sig_type and sig_type not in VALID_SIGNAL_TYPES:
        issues.append(f"signal_type '{sig_type}' not in canonical set")

    beneficiary = signal.get("beneficiary")
    if beneficiary and beneficiary not in VALID_BENEFICIARIES:
        issues.append(f"beneficiary '{beneficiary}' not in canonical set")

    valence = signal.get("emotional_valence")
    if valence and valence not in VALID_VALENCES:
        issues.append(f"emotional_valence '{valence}' not in canonical set")

    time_horizon = signal.get("time_horizon")
    if time_horizon and time_horizon not in VALID_TIME_HORIZONS:
        issues.append(f"time_horizon '{time_horizon}' not in canonical set")

    return len(issues) == 0, issues


def schema_conformance_report(signals: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a conformance report for a list of signals."""
    total = len(signals)
    valid_signals = [s for s in signals if s.get("quality") == "valid"]
    n_valid = len(valid_signals)

    non_canonical: dict[str, dict[str, int]] = {
        "primary_pillar": {},
        "signal_type": {},
        "beneficiary": {},
        "emotional_valence": {},
        "time_horizon": {},
    }

    n_conforming = 0
    n_non_conforming = 0

    for s in valid_signals:
        is_ok, issues = validate_signal(s)
        if is_ok:
            n_conforming += 1
        else:
            n_non_conforming += 1
            for issue in issues:
                for field in non_canonical:
                    if issue.startswith(field):
                        val = s.get(field, "?")
                        non_canonical[field][val] = non_canonical[field].get(val, 0) + 1

    # Filter out empty dimension reports
    non_canonical = {k: v for k, v in non_canonical.items() if v}

    return {
        "total_signals": total,
        "valid_signals": n_valid,
        "conforming": n_conforming,
        "non_conforming": n_non_conforming,
        "conformance_pct": round(100 * n_conforming / n_valid, 1) if n_valid else 0.0,
        "non_canonical_values": non_canonical,
    }
