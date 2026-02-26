"""
Redact real wishes, names, and translated text from all TAOTF data files.
Run from project root: python scripts/redact_sensitive_data.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def redact_jsonl(path: Path, keys_to_clear: list[str]) -> None:
    """Set keys to null or empty string; write back."""
    lines_out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                lines_out.append(line)
                continue
            for k in keys_to_clear:
                if k in obj:
                    obj[k] = None if k == "translated" else ""
            lines_out.append(json.dumps(obj, ensure_ascii=False))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + ("\n" if lines_out else ""))
    print(f"  Redacted {path.name}: {keys_to_clear}")


def redact_xlsx(path: Path, columns_to_clear: list[str]) -> None:
    """Clear columns that may contain wish text or names."""
    try:
        import pandas as pd
    except ImportError:
        print(f"  Skip {path.name}: pandas required for xlsx")
        return
    if not path.exists():
        print(f"  Skip {path.name}: file not found")
        return
    try:
        with pd.ExcelFile(path, engine="openpyxl") as xl:
            sheet_names = xl.sheet_names
            sheets = {sheet: pd.read_excel(xl, sheet_name=sheet) for sheet in sheet_names}
    except Exception as e:
        print(f"  Skip {path.name}: could not read ({e})")
        return
    for sheet, df in sheets.items():
        for col in columns_to_clear:
            if col in df.columns:
                df[col] = ""
    try:
        with pd.ExcelWriter(path, engine="openpyxl") as w:
            for sheet, df in sheets.items():
                df.to_excel(w, sheet_name=sheet, index=False)
        print(f"  Redacted xlsx {path.name}: cleared {columns_to_clear}")
    except Exception as e:
        print(f"  Skip {path.name}: could not write ({e})")


def main():
    root = PROJECT_ROOT

    # ─── JSONL ─────────────────────────────────────────────────────────────
    # taotf_signals.jsonl: raw wish text and translations
    signals_jsonl = root / "taotf_signals.jsonl"
    if signals_jsonl.exists():
        redact_jsonl(signals_jsonl, ["translated", "_raw_text"])
    else:
        print(f"  Skip {signals_jsonl.name}: not found")

    # test_data/real_from_middle.jsonl
    real_middle = root / "test_data" / "real_from_middle.jsonl"
    if real_middle.exists():
        redact_jsonl(real_middle, ["translated"])

    # unreal_agent.jsonl has no wish/translated text; skip
    # compare_payload.json has no wish text; skip
    # report_*.json have only aggregates; skip

    # ─── XLSX ─────────────────────────────────────────────────────────────
    # wishes.xlsx: wish_text may contain names and real wishes
    wishes_xlsx = root / "wishes.xlsx"
    if wishes_xlsx.exists():
        redact_xlsx(wishes_xlsx, ["wish_text"])

    # taotf_signals.xlsx: may have wish_text (from merge), translated
    taotf_xlsx = root / "taotf_signals.xlsx"
    if taotf_xlsx.exists():
        redact_xlsx(taotf_xlsx, ["wish_text", "translated", "_raw_text", "display_text"])

    print("Done.")


if __name__ == "__main__":
    main()
