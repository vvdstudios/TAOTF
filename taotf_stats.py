"""
TAOTF Statistics — Shared statistical functions used by API, verification, and ADI script.

Eliminates the 3-way duplication of JS divergence and distribution code, and adds
bootstrap confidence intervals and permutation significance testing.

By Vivid Studio (https://vividstudio.me)
"""
from __future__ import annotations

import math
import random
from collections import Counter
from typing import Any, Callable


def counts_to_probs(counts: dict[str, float]) -> dict[str, float]:
    """Convert count dict to probability dict (sums to 1.0)."""
    total = sum(counts.values()) or 1
    return {k: v / total for k, v in counts.items()}


def js_divergence_normalized(p_counts: dict[str, int | float], q_counts: dict[str, int | float]) -> float:
    """Jensen-Shannon divergence normalized to [0, 1]. 0 = identical, 1 = max divergence."""
    keys = set(p_counts) | set(q_counts)
    if not keys:
        return 0.0
    p_total = sum(p_counts.get(k, 0) for k in keys) or 1
    q_total = sum(q_counts.get(k, 0) for k in keys) or 1
    P = {k: (p_counts.get(k, 0) or 0) / p_total for k in keys}
    Q = {k: (q_counts.get(k, 0) or 0) / q_total for k in keys}
    M = {k: (P[k] + Q[k]) / 2 for k in keys}
    js = 0.0
    for k in keys:
        if M[k] > 0:
            if P[k] > 0:
                js += P[k] * math.log(P[k] / M[k])
            if Q[k] > 0:
                js += Q[k] * math.log(Q[k] / M[k])
    js *= 0.5
    max_js = math.log(2)
    return (js / max_js) if max_js else 0.0


DIMENSIONS = ("pillar", "beneficiary", "emotional_valence", "signal_type")

_DIMENSION_KEYS = {
    "pillar": "primary_pillar",
    "beneficiary": "beneficiary",
    "emotional_valence": "emotional_valence",
    "signal_type": "signal_type",
}


def build_distributions(signals: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Build count distributions for all four taxonomy dimensions."""
    result: dict[str, dict[str, int]] = {}
    for dim in DIMENSIONS:
        field = _DIMENSION_KEYS[dim]
        counts = Counter(s.get(field) for s in signals if s.get(field))
        result[dim] = {str(k): v for k, v in counts.items()}
    return result


def alignment_score(signal: dict[str, Any], reference_signals: list[dict[str, Any]]) -> float:
    """Compare one signal's dimensions to reference distribution. Returns 0-1 (1 = aligned)."""
    valid_ref = [s for s in reference_signals if s.get("quality") == "valid"]
    if not valid_ref:
        return 0.0
    ref_dist = build_distributions(valid_ref)
    total = 0.0
    for dim in DIMENSIONS:
        field = _DIMENSION_KEYS[dim]
        val = signal.get(field) or "unknown"
        one = {val: 1.0}
        js = js_divergence_normalized(ref_dist[dim], one)
        total += 1.0 - js
    return total / len(DIMENSIONS)


def compute_divergences(
    human_dist: dict[str, dict[str, int]],
    submitted_dist: dict[str, dict[str, int]],
) -> dict[str, float]:
    """Compute JS divergence per dimension between two distribution sets."""
    return {
        dim: js_divergence_normalized(human_dist.get(dim, {}), submitted_dist.get(dim, {}))
        for dim in DIMENSIONS
    }


def aspiration_alignment_score(divergences: dict[str, float]) -> float:
    """Compute overall alignment score from per-dimension divergences."""
    alignments = [1.0 - divergences.get(dim, 0.0) for dim in DIMENSIONS]
    return sum(alignments) / len(alignments)


# ── Bootstrap confidence intervals ───────────────────────────────────────────

def bootstrap_ci(
    values: list[float],
    stat_fn: Callable[[list[float]], float] | None = None,
    n_boot: int = 1000,
    ci: float = 0.95,
    seed: int | None = 42,
) -> tuple[float, float, float]:
    """
    Bootstrap confidence interval for a statistic.

    Args:
        values: observed values
        stat_fn: function that computes the statistic (default: mean)
        n_boot: number of bootstrap samples
        ci: confidence level (e.g. 0.95 for 95% CI)
        seed: random seed for reproducibility

    Returns:
        (point_estimate, ci_lower, ci_upper)
    """
    if stat_fn is None:
        stat_fn = lambda v: sum(v) / len(v) if v else 0.0

    if not values:
        return 0.0, 0.0, 0.0

    rng = random.Random(seed)
    point = stat_fn(values)
    boot_stats = []
    n = len(values)
    for _ in range(n_boot):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        boot_stats.append(stat_fn(sample))
    boot_stats.sort()
    alpha = 1.0 - ci
    lo_idx = int(alpha / 2 * n_boot)
    hi_idx = int((1.0 - alpha / 2) * n_boot) - 1
    lo_idx = max(0, min(lo_idx, n_boot - 1))
    hi_idx = max(0, min(hi_idx, n_boot - 1))
    return point, boot_stats[lo_idx], boot_stats[hi_idx]


# ── Permutation significance test ────────────────────────────────────────────

def compare_with_significance(
    human_signals: list[dict[str, Any]],
    submitted_signals: list[dict[str, Any]],
    n_boot: int = 1000,
    seed: int | None = 42,
) -> dict[str, dict[str, Any]]:
    """
    Compare human and submitted signal distributions with bootstrap CIs and
    permutation p-values per dimension.

    Returns dict keyed by dimension, each containing:
        - divergence: observed JS divergence
        - ci_lower, ci_upper: 95% bootstrap CI on divergence
        - p_value: proportion of permutation samples with divergence >= observed
    """
    rng = random.Random(seed)
    h_valid = [s for s in human_signals if s.get("quality") == "valid"]
    h_dist = build_distributions(h_valid)
    s_dist = build_distributions(submitted_signals)
    observed = compute_divergences(h_dist, s_dist)

    combined = h_valid + submitted_signals
    n_human = len(h_valid)
    n_total = len(combined)

    result: dict[str, dict[str, Any]] = {}

    for dim in DIMENSIONS:
        field = _DIMENSION_KEYS[dim]
        obs_div = observed[dim]

        # Bootstrap CI on human distribution (resample human, compare to submitted)
        boot_divs: list[float] = []
        for _ in range(n_boot):
            sample = [h_valid[rng.randint(0, n_human - 1)] for _ in range(n_human)]
            sample_dist = dict(Counter(s.get(field) for s in sample if s.get(field)))
            boot_divs.append(js_divergence_normalized(sample_dist, s_dist.get(dim, {})))

        boot_divs.sort()
        lo_idx = max(0, int(0.025 * n_boot))
        hi_idx = min(n_boot - 1, int(0.975 * n_boot) - 1)

        # Permutation p-value: shuffle combined, split, compute divergence
        n_extreme = 0
        for _ in range(n_boot):
            perm = list(combined)
            rng.shuffle(perm)
            perm_h = perm[:n_human]
            perm_s = perm[n_human:]
            perm_h_dist = dict(Counter(s.get(field) for s in perm_h if s.get(field)))
            perm_s_dist = dict(Counter(s.get(field) for s in perm_s if s.get(field)))
            perm_div = js_divergence_normalized(perm_h_dist, perm_s_dist)
            if perm_div >= obs_div:
                n_extreme += 1

        result[dim] = {
            "divergence": round(obs_div, 4),
            "ci_lower": round(boot_divs[lo_idx], 4),
            "ci_upper": round(boot_divs[hi_idx], 4),
            "p_value": round(n_extreme / n_boot, 4),
        }

    return result
