#!/usr/bin/env python3
"""
TAOTF Aspiration Divergence Index (ADI) — Human vs Agent intention comparison.

By Vivid Studio (https://vividstudio.me)

Standalone, reproducible benchmark: load human and agent/synthetic signal JSONL,
compute per-dimension Jensen-Shannon divergence with bootstrap CIs and permutation
p-values, plus a single aspiration_alignment_score.

Usage:
  python scripts/aspiration_divergence.py --human taotf_signals.jsonl --agent agent_wishes.jsonl
  python scripts/aspiration_divergence.py --human taotf_signals.jsonl --agent agent_wishes.jsonl -o report.json

Output: stdout summary + optional JSON report.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add parent dir to path so we can import shared modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from taotf_stats import (
    counts_to_probs,
    build_distributions,
    compute_divergences,
    aspiration_alignment_score,
    compare_with_significance,
    DIMENSIONS,
)


def load_signals(path: Path, quality_filter: str | None = "valid") -> list[dict]:
    signals = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if quality_filter is None or obj.get("quality") == quality_filter:
                    signals.append(obj)
            except json.JSONDecodeError:
                continue
    return signals


def run(human_path: Path, agent_path: Path, output_path: Path | None) -> dict:
    human = load_signals(human_path)
    agent = load_signals(agent_path, quality_filter=None)
    if not human:
        raise SystemExit(f"No valid human signals in {human_path}")
    if not agent:
        raise SystemExit(f"No signals in {agent_path}")

    h_dist = build_distributions(human)
    a_dist = build_distributions(agent)

    divergences = compute_divergences(h_dist, a_dist)
    alignment = {dim: round(1.0 - divergences[dim], 4) for dim in DIMENSIONS}
    score = round(aspiration_alignment_score(divergences), 4)

    # Statistical rigor: bootstrap CIs and permutation p-values
    sig_results = compare_with_significance(human, agent, n_boot=1000)

    report = {
        "human_n": len(human),
        "agent_n": len(agent),
        "human_distribution": {k: counts_to_probs(v) for k, v in h_dist.items()},
        "agent_distribution": {k: counts_to_probs(v) for k, v in a_dist.items()},
        "divergence": {},
        "alignment_per_dimension": alignment,
        "aspiration_alignment_score": score,
        "interpretation": (
            "1.0 = aspirations match human distribution; 0.0 = maximally divergent. "
            "p_value < 0.05 indicates statistically significant divergence. "
            "CI bounds are 95% bootstrap confidence intervals on divergence."
        ),
    }

    # Merge divergences with CIs and p-values
    for dim in DIMENSIONS:
        report["divergence"][dim] = {
            "value": round(divergences[dim], 4),
            "ci_lower": sig_results[dim]["ci_lower"],
            "ci_upper": sig_results[dim]["ci_upper"],
            "p_value": sig_results[dim]["p_value"],
        }

    # Stdout summary
    print("TAOTF Aspiration Divergence Index (ADI)")
    print("=" * 60)
    print(f"Human signals:  {report['human_n']}")
    print(f"Agent signals:  {report['agent_n']}")
    print()
    print("Divergence (0 = same, 1 = max):")
    for dim in DIMENSIONS:
        d = report["divergence"][dim]
        print(f"  {dim:<22} {d['value']:.4f}  "
              f"[{d['ci_lower']:.4f}, {d['ci_upper']:.4f}]  "
              f"p={d['p_value']:.4f}")
    print()
    print("Alignment per dimension (1 = aligned):")
    for dim, v in report["alignment_per_dimension"].items():
        print(f"  {dim:<22} {v:.4f}")
    print()
    print(f"Aspiration Alignment Score: {report['aspiration_alignment_score']}")
    print("  (1.0 = match human aspiration distribution; 0.0 = maximally divergent)")
    print()

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Report written to {output_path}")

    return report


def main():
    p = argparse.ArgumentParser(description="TAOTF Aspiration Divergence Index — human vs agent intention comparison")
    p.add_argument("--human", "-H", type=Path, required=True, help="Path to human TAOTF signals JSONL")
    p.add_argument("--agent", "-A", type=Path, required=True, help="Path to agent/synthetic signals JSONL (same schema)")
    p.add_argument("-o", "--output", type=Path, default=None, help="Write full JSON report here")
    args = p.parse_args()
    if not args.human.exists():
        p.error(f"File not found: {args.human}")
    if not args.agent.exists():
        p.error(f"File not found: {args.agent}")
    run(args.human, args.agent, args.output)


if __name__ == "__main__":
    main()
