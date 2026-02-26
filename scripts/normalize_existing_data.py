#!/usr/bin/env python3
"""
One-time migration script: normalize all signals in taotf_signals.jsonl to canonical taxonomy.

Reads the JSONL, applies normalize_signal() to every record, backs up the original,
and writes the normalized version in-place. Prints a before/after conformance report.

Usage:
    python scripts/normalize_existing_data.py
    python scripts/normalize_existing_data.py --input taotf_signals.jsonl
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add parent dir to path so we can import taotf_schema
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from taotf_schema import normalize_signal, schema_conformance_report


def main():
    parser = argparse.ArgumentParser(description="Normalize TAOTF signals to canonical taxonomy")
    parser.add_argument("--input", "-i", type=Path, default=Path("taotf_signals.jsonl"),
                        help="Path to signals JSONL (default: taotf_signals.jsonl)")
    args = parser.parse_args()

    input_path = args.input
    if not input_path.exists():
        print(f"ERROR: {input_path} not found.")
        sys.exit(1)

    # Read all signals
    signals = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                signals.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    print(f"Loaded {len(signals)} signals from {input_path}")
    print()

    # Before report
    print("=== BEFORE NORMALIZATION ===")
    before = schema_conformance_report(signals)
    print(f"  Total:          {before['total_signals']}")
    print(f"  Valid:          {before['valid_signals']}")
    print(f"  Conforming:     {before['conforming']}")
    print(f"  Non-conforming: {before['non_conforming']}")
    print(f"  Conformance:    {before['conformance_pct']}%")
    if before["non_canonical_values"]:
        for field, vals in before["non_canonical_values"].items():
            print(f"\n  Non-canonical {field}:")
            for val, count in sorted(vals.items(), key=lambda x: -x[1]):
                print(f"    {count:4d}  {val!r}")
    print()

    # Normalize
    normalized = [normalize_signal(s) for s in signals]

    # After report
    print("=== AFTER NORMALIZATION ===")
    after = schema_conformance_report(normalized)
    print(f"  Total:          {after['total_signals']}")
    print(f"  Valid:          {after['valid_signals']}")
    print(f"  Conforming:     {after['conforming']}")
    print(f"  Non-conforming: {after['non_conforming']}")
    print(f"  Conformance:    {after['conformance_pct']}%")
    if after["non_canonical_values"]:
        for field, vals in after["non_canonical_values"].items():
            print(f"\n  Non-canonical {field}:")
            for val, count in sorted(vals.items(), key=lambda x: -x[1]):
                print(f"    {count:4d}  {val!r}")
    print()

    # Backup original
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = input_path.with_suffix(f".backup_{timestamp}.jsonl")
    shutil.copy2(input_path, backup_path)
    print(f"Backup saved to {backup_path}")

    # Write normalized
    with open(input_path, "w", encoding="utf-8") as f:
        for s in normalized:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"Wrote {len(normalized)} normalized signals to {input_path}")
    print(f"\nDone. Conformance improved from {before['conformance_pct']}% to {after['conformance_pct']}%.")


if __name__ == "__main__":
    main()
