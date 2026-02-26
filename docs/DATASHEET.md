# Datasheet for TAOTF Signal Dataset

Following the framework from Gebru et al. (2021), "Datasheets for Datasets."

---

## Motivation

**Purpose:** Capture structured aspiration signals from human wishes — what people want for the future — to enable research on human intention, agent alignment, and community planning.

**Creators:** Vivid Studio (vividstudio.me), in collaboration with Omnia Experience Centers (first deployment: Sohar, Oman; expanding to more cities).

**Funding:** Self-funded research project by Vivid Studio.

---

## Composition

**What does the dataset represent?** Each record is a structured signal extracted from a handwritten wish. Fields include: topic (pillar), aspiration type, who the wish is for (beneficiary), emotional tone, urgency, time horizon, and key themes.

**How many instances?** ~2,269 signals (as of version 2026.1). Approximately 91% classified as "valid," 8% as "noise," <1% as "error."

**What data does each instance consist of?**
- `wish_id`: UUID
- `translated`: English translation (if original was Arabic/mixed)
- `quality`: valid, noise, or error
- `primary_pillar`: One of 10 canonical pillars (e.g., Education & Knowledge, Human Connection)
- `signal_type`: One of 5 types (e.g., self_directed_aspiration, connection_aspiration)
- `beneficiary`: self, family, community, humanity, or unknown
- `emotional_valence`: hope, longing, urgency, gratitude, grief, joy, or neutral
- `urgency_score`: 0-1 float
- `time_horizon`: immediate, near_term, long_term, or unspecified
- `key_themes`: 1-3 short English theme labels
- `_raw_text`: Original wish text (may be withheld in public releases)
- `_written_at`: ISO 8601 timestamp

**Is any information missing?** Some wishes could not be classified and are marked as "noise" or "error." Raw text may be omitted in public releases for privacy.

**Does the dataset contain data that might be considered confidential?** Raw wish text could potentially identify individuals if very specific. The `_raw_text` field can be withheld. All other fields are aggregated/categorical and not personally identifiable.

---

## Collection Process

**How was the data collected?** Visitors to Omnia Experience Centers wrote wishes by hand. These were digitized (transcribed) into a spreadsheet with columns: `id`, `wish_text`. The raw wishes (`wishes.xlsx`) are **not open source** — only the structured signals (`taotf_signals.jsonl`) are publicly released.

**Who collected the data?** Staff at Omnia Experience Centers; digitization by the TAOTF project team.

**Over what timeframe?** Collection period is associated with the Omnia Experience Center's operational period. Exact dates are not published.

**Was consent obtained?** Participation was voluntary. Visitors were informed their wishes would be part of an archive. No personally identifying information was collected.

**Languages:** Arabic, English, and mixed (Arabic-English).

---

## Preprocessing

**What preprocessing was done?**
1. **Pre-filtering:** Removal of URLs, gibberish, and entries with fewer than 3 meaningful characters.
2. **LLM classification:** Each wish was processed through an LLM (initially GPT-4o-mini, now configurable via Ollama or OpenAI) that assigned all structured fields (pillar, signal type, beneficiary, valence, themes, etc.).
3. **Normalization:** A post-processing step maps non-canonical taxonomy values to the 10 canonical pillars and 5 canonical signal types. For example, "Economy & Prosperity" is normalized to "Nation & Society." See `taotf_schema.py` for the full normalization map.

**Was the raw data saved?** Yes, in `wishes.xlsx`. The `_raw_text` field in signals preserves the original text.

**Known issues with preprocessing:**
- LLM classification is imperfect. The initial GPT-4o-mini run produced 38 distinct pillar names instead of the defined 10, requiring normalization.
- No inter-annotator agreement was measured (single LLM pass, no human verification).
- Classification quality depends on the LLM model used.

---

## Uses

**Intended uses:**
- Research on human aspiration and intention
- Agent alignment benchmarking (comparing agent-stated aspirations to human distribution)
- Community planning and policy analysis
- Educational use in AI ethics and alignment courses

**Uses to avoid:**
- Individual profiling or targeting
- Marketing or commercial targeting based on aspiration data
- Claiming the dataset is globally representative (it is from one site in Oman)
- Using alignment scores as sole proof of agent safety

---

## Distribution

**How is the dataset distributed?** As `taotf_signals.jsonl` (newline-delimited JSON) in the project repository.

**License:** Creative Commons Attribution 4.0 International (CC BY 4.0).

**Will the dataset be updated?** Possibly. Version numbers (e.g., 2026.1) track schema changes. New collection rounds may produce updated datasets.

---

## Maintenance

**Who maintains the dataset?** Vivid Studio (vividstudio.me).

**How can errors be reported?** Via the project's issue tracker.

**Will older versions be available?** Not guaranteed. Users should archive versions they depend on.

---

## Limitations

- **Limited sites:** Initial data was collected at Omnia Experience Center in Sohar, Oman (expanding to more cities). The dataset reflects the aspirations of visitors to these centers, not global populations.
- **Stated preferences only:** People write what they *say* they want. This may differ from their actual priorities or behaviors.
- **LLM classification:** Automated, with known taxonomy drift. No human annotation or inter-rater reliability.
- **Language bias:** The LLM may perform differently on Arabic vs. English text.
- **Self-selection:** Participants chose to write wishes; non-participants' aspirations are unrepresented.
- **Temporal snapshot:** The data reflects aspirations at a specific time. Aspirations change.

---

*By [Vivid Studio](https://vividstudio.me). See [DATASET.md](DATASET.md) for schema details.*
