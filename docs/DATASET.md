# TAOTF Dataset

This document describes the TAOTF (The Archive of the Future) signal dataset: schema, collection, and license.

## Overview

- **Purpose:** Structured aspiration signals derived from human wishes (preferred futures, not predicted futures).
- **Collection context:** Omnia Experience Centers (first deployment: Sohar, Oman; expanding to more cities); wishes in Arabic, English, or mixed.
- **Processing:** Raw text → quality filter → LLM-based tagging (pillars, signal type, beneficiary, emotional valence, themes) → normalization → JSONL + Excel.
- **Normalization:** A post-processing step maps non-canonical taxonomy values to the 10 canonical pillars. The initial LLM run produced 38 distinct pillar names; normalization maps these to the canonical set. See `taotf_schema.py` for the full normalization map.

## Files

| File | Description |
|------|-------------|
| `taotf_signals.jsonl` | One JSON object per line; full schema below. |
| `taotf_signals.xlsx` | Same data plus summary sheets (pillars, signal types, beneficiary, top themes). |
| `wishes.xlsx` | Raw input (columns: `id`, `wish_text`). **Not open source** — private. |

## Schema (per signal)

| Field | Type | Description |
|-------|------|-------------|
| `wish_id` | string | Unique identifier (UUID from ingestion). |
| `translated` | string \| null | English translation if input was Arabic/mixed; else null. |
| `quality` | string | `valid` \| `noise` \| `error`. |
| `primary_pillar` | string | One of 10 TAOTF pillars. |
| `secondary_pillars` | string[] | Additional pillars (can be empty). |
| `primary_pillar_confidence` | float | 0–1. |
| `signal_type` | string | protective_aspiration, access_aspiration, transformation_aspiration, connection_aspiration, self_directed_aspiration. |
| `beneficiary` | string | self, family, community, humanity, unknown. |
| `emotional_valence` | string | hope, longing, urgency, gratitude, grief, joy, neutral. |
| `urgency_score` | float | 0–1. |
| `time_horizon` | string | immediate, near_term, long_term, unspecified. |
| `key_themes` | string[] | 1–3 short English theme labels. |
| `_raw_text` | string | Original wish text (internal; may be omitted in public exports for privacy). |
| `_written_at` | string | ISO 8601 timestamp of record creation. |

## Pillars (controlled vocabulary)

Health & Longevity · Home & Living · Education & Knowledge · Energy & Sustainability · Space & Exploration · Nation & Society · Environment & Planet · Human Connection · Digital Identity · Human-AI Collaboration

## Data governance

- **Anonymization:** No PII is retained by design; optional removal or hashing of `_raw_text` in public dataset releases.
- **Use:** Collective signal mapping over individual profiling; longitudinal civilization tracking; research and archival.
- **No resale:** Data is not sold; shared under the license below.

## Limitations

- **Limited sites:** Initial data from Omnia Experience Center, Sohar, Oman (expanding to more cities) — not globally representative.
- **LLM classification:** Automated, with known taxonomy drift. No human annotation or inter-rater reliability measured.
- **Stated preferences:** What people say they want, not necessarily what they do.
- See [DATASHEET.md](DATASHEET.md) for the full datasheet following Gebru et al. (2021).

## License

The TAOTF signal dataset is released under **Creative Commons Attribution 4.0 International (CC BY 4.0)**.

- You may share and adapt the data with attribution.
- See: https://creativecommons.org/licenses/by/4.0/

## Citation

```text
TAOTF — The Archive of the Future. Dataset (Signals). Omnia / TAOTF Project. Version 2026.1. CC BY 4.0.
```

## Versioning

- **2026.1:** Initial schema; pillars, signal types, beneficiary, emotional valence, key_themes. Normalization pipeline added.

---

*By [Vivid Studio](https://vividstudio.me).*
