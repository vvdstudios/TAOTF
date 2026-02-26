# TAOTF for Agentic AI — Intentions, Alignment & Human-Robot Comparison

TAOTF is a **structured human aspiration dataset**. For agentic AI this creates three uses: (1) **steering** agents toward what humans want, (2) **benchmarking** how aligned agent intentions are to humans, and (3) **reproducible comparison** via the Aspiration Divergence Index (ADI).

---

## 1. Intentions endpoint — steer agents toward human-preferred futures

**Endpoint:** `GET /v1/intentions`

**Purpose:** One compact, agent-optimized summary of "what humans want" (pillars, beneficiary, emotional valence, signal type, top themes). No pagination, minimal payload.

**Use cases:**
- **Reward shaping:** Use pillar/beneficiary/valence distributions as a prior or auxiliary reward.
- **Goal conditioning:** Pass distributions into a planner or LLM context.
- **UI / dashboards:** Show "human aspiration snapshot" next to agent behavior.

---

## 2. Compare endpoint — human vs robot intention comparison

**Endpoint:** `POST /v1/compare`

**Purpose:** Submit a set of **pre-tagged** aspiration signals (e.g. from an AI agent). The API compares their distribution to the human TAOTF distribution and returns:
- Per-dimension **divergence** (Jensen-Shannon, normalized 0-1) with **95% bootstrap confidence intervals** and **permutation p-values**
- Per-dimension **alignment** (1 - divergence)
- A single **aspiration_alignment_score** (average of the four alignments)

**Use cases:**
- **Alignment benchmark:** "How aligned are this model's stated aspirations to real human aspirations?"
- **A/B tests:** Compare two agent designs by their aspiration distributions.
- **Longitudinal tracking:** Track alignment over model checkpoints.

---

## 3. Aspiration Divergence Index (ADI) — reproducible comparison

**What it is:** A reproducible, offline benchmark. No API key, no server.

**Script:** `scripts/aspiration_divergence.py`

```bash
python scripts/aspiration_divergence.py --human taotf_signals.jsonl --agent agent_wishes.jsonl -o report.json
```

**Output:** Summary with divergence per dimension (with CIs and p-values), alignment scores, and optional JSON report.

**Why this matters:**
- **Reproducibility:** Fixed script + fixed human baseline = comparable numbers across labs.
- **No lock-in:** Works with any TAOTF-shaped JSONL; no dependency on a live API.
- **Statistical rigor:** Bootstrap CIs and permutation p-values on divergence values.

---

## 4. Methodology — divergence and alignment score

- **Distributions:** For human and agent signals we build four discrete distributions: pillar, beneficiary, emotional_valence, signal_type (counts → probabilities).
- **Divergence:** Jensen-Shannon divergence between human and agent distribution for each dimension, normalized to [0, 1].
- **Alignment per dimension:** `1 - divergence`.
- **Aspiration Alignment Score:** Arithmetic mean of the four alignment values.
- **Bootstrap CI:** Resample the human distribution 1000 times, recompute divergence, report 2.5th and 97.5th percentiles.
- **Permutation p-value:** Shuffle combined signals, split into pseudo-human and pseudo-agent groups, compute divergence. P-value = fraction of permutations with divergence >= observed.

**Methodology note:** The equal weighting of 4 dimensions is an arbitrary choice. Different applications may want to weight dimensions differently (e.g., prioritize pillar alignment over valence alignment). The raw per-dimension scores are always available for custom weighting.

---

## 5. Longitudinal tracking

- Version human baselines (e.g. `taotf_signals_2026Q1.jsonl`).
- Run ADI or `/v1/compare` for each new agent checkpoint.
- Track `aspiration_alignment_score` over time.

---

## 6. Relation to other benchmarks

- **Preference-based alignment:** TAOTF is **distributional**: we compare the *distribution* of aspiration dimensions. This complements preference-based benchmarks by focusing on **stated intentions**.
- **Limitations vs. other benchmarks:** TAOTF measures *stated* aspiration from Omnia Experience Centers (initial: Sohar, Oman; expanding). It does not measure behavior, reasoning, or safety.

---

## 7. Citation and research use

```text
TAOTF — The Archive of the Future. Intentions API, Compare API, and Aspiration Divergence Index (ADI).
Omnia / TAOTF Project. Version 2026.1. https://github.com/[org]/taotf
```

---

**Summary:** Use **intentions** to steer agents, **compare** to benchmark alignment, and **ADI** for reproducible comparison. Together they provide a distributional layer for comparing human and agent aspirations — one signal among many for alignment work.

*By [Vivid Studio](https://vividstudio.me). See [EXAMPLES.md](EXAMPLES.md) for API and ADI examples.*
