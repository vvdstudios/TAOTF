#!/usr/bin/env python3
"""
Generate a plain-language policy brief from TAOTF signals.

Outputs a Markdown summary for non-technical audiences (policy makers, planners).
Covers: top aspirations, who people wish for, emotional tone, key themes, methodology.

Usage:
    python scripts/generate_policy_brief.py
    python scripts/generate_policy_brief.py --input taotf_signals.jsonl --output brief.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from taotf_schema import normalize_signal


def load_valid_signals(path: Path) -> list[dict]:
    signals = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                obj = normalize_signal(obj)
                if obj.get("quality") == "valid":
                    signals.append(obj)
            except json.JSONDecodeError:
                continue
    return signals


def generate_brief(signals: list[dict]) -> str:
    n = len(signals)
    pillars = Counter(s.get("primary_pillar") for s in signals if s.get("primary_pillar"))
    beneficiaries = Counter(s.get("beneficiary") for s in signals if s.get("beneficiary"))
    valences = Counter(s.get("emotional_valence") for s in signals if s.get("emotional_valence"))
    types = Counter(s.get("signal_type") for s in signals if s.get("signal_type"))

    all_themes: list[str] = []
    for s in signals:
        t = s.get("key_themes")
        if isinstance(t, list):
            all_themes.extend(t)
    top_themes = Counter(all_themes).most_common(15)

    lines = []
    lines.append("# TAOTF Community Aspiration Brief")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d')} | Source: Omnia Experience Centers*")
    lines.append(f"*Based on {n:,} valid aspiration signals*")
    lines.append("")

    # Top aspirations
    lines.append("## What People Want Most")
    lines.append("")
    for pillar, count in pillars.most_common(5):
        pct = round(100 * count / n, 1)
        lines.append(f"- **{pillar}** — {pct}% of aspirations ({count:,} signals)")
    lines.append("")

    # Who they wish for
    lines.append("## Who People Wish For")
    lines.append("")
    for ben, count in beneficiaries.most_common():
        pct = round(100 * count / n, 1)
        lines.append(f"- **{ben.capitalize()}** — {pct}% ({count:,})")
    lines.append("")

    # Emotional tone
    lines.append("## Emotional Tone")
    lines.append("")
    top_val, top_val_n = valences.most_common(1)[0]
    top_val_pct = round(100 * top_val_n / n, 1)
    lines.append(f"The dominant emotional tone is **{top_val}** ({top_val_pct}%), ")
    others = valences.most_common()[1:4]
    others_str = ", ".join(f"{v} ({round(100*c/n,1)}%)" for v, c in others)
    lines.append(f"followed by {others_str}.")
    lines.append("")

    # Key themes
    lines.append("## Key Themes")
    lines.append("")
    for theme, count in top_themes:
        lines.append(f"- {theme} ({count:,} mentions)")
    lines.append("")

    # Type of aspiration
    lines.append("## Types of Aspiration")
    lines.append("")
    type_labels = {
        "self_directed_aspiration": "Self-directed (personal growth, goals)",
        "connection_aspiration": "Connection (relationships, community bonds)",
        "transformation_aspiration": "Transformation (change, improvement)",
        "access_aspiration": "Access (resources, opportunities, rights)",
        "protective_aspiration": "Protective (safety, preservation, security)",
    }
    for sig_type, count in types.most_common():
        pct = round(100 * count / n, 1)
        label = type_labels.get(sig_type, sig_type)
        lines.append(f"- **{label}** — {pct}%")
    lines.append("")

    # Methodology note
    lines.append("## Methodology Note")
    lines.append("")
    lines.append("This brief summarizes structured aspiration signals extracted from handwritten wishes ")
    lines.append("collected at Omnia Experience Centers. Wishes were written in Arabic, ")
    lines.append("English, or mixed language. Each wish was processed through an LLM-based classification ")
    lines.append("pipeline that assigns a primary pillar (topic), signal type, beneficiary, emotional valence, ")
    lines.append("and key themes. The classification is automated and may contain errors.")
    lines.append("")
    lines.append("**Limitations:**")
    lines.append("- Limited collection sites (initial: Sohar, Oman; expanding) — not representative of global populations")
    lines.append("- Stated aspirations only — what people *say* they want, not necessarily what they do")
    lines.append("- LLM-dependent classification — no inter-annotator agreement measured")
    lines.append("- Self-selected participants — visitors to Omnia Experience Centers")
    lines.append("")
    lines.append("---")
    lines.append("*TAOTF — The Archive of the Future. By Vivid Studio (vividstudio.me)*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate a policy brief from TAOTF signals")
    parser.add_argument("--input", "-i", type=Path, default=Path("taotf_signals.jsonl"))
    parser.add_argument("--output", "-o", type=Path, default=None)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: {args.input} not found.")
        sys.exit(1)

    signals = load_valid_signals(args.input)
    if not signals:
        print("No valid signals found.")
        sys.exit(1)

    brief = generate_brief(signals)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(brief)
        print(f"Brief written to {args.output}")
    else:
        print(brief)


if __name__ == "__main__":
    main()
