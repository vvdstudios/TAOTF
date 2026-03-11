# TAOTF — The Archive of the Future

**Mapping where humanity wants to go.**

TAOTF is an LLM-assisted classification pipeline and API for structuring human wishes into aspiration signals. It captures *preferred futures* from wishes collected at Omnia Experience Centers.

*By [Vivid Studio](https://vividstudio.me)*

[![Status: ACTIVE](https://img.shields.io/badge/status-ACTIVE-green)](#) [![Version: 2026.1](https://img.shields.io/badge/version-2026.1-blue)](#) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## What's in this repo

| Component | Description |
|-----------|-------------|
| **Pipeline** (`index.py`) | Batch processing: raw wishes → structured aspiration signals (pillars, valence, themes). Uses Ollama (default) or OpenAI for LLM tagging; outputs JSONL + Excel. |
| **API** (`api.py`) | REST API to query signals, stats, pillars, themes; **intentions** (agent steering), **compare** (human vs agent alignment), **export** (CSV/JSON), **community-profile** (cross-tabulations). |
| **Dataset** | `taotf_signals.jsonl` (2,269 structured signals, open source). Raw wishes (`wishes.xlsx`) are **not included** — they are private. See [docs/DATASET.md](docs/DATASET.md) and [docs/DATASHEET.md](docs/DATASHEET.md). |
| **Agentic AI** | [Intentions](#agentic-ai--intentions--alignment) + [Compare](#agentic-ai--intentions--alignment) endpoints; [Aspiration Divergence Index](docs/AGENTIC_AI.md#3-aspiration-divergence-index-adi--reproducible-comparison) script for reproducible human-robot intention comparison. See [docs/AGENTIC_AI.md](docs/AGENTIC_AI.md). |
| **Agent verification** | **Dynamic probes** + **closed-box verification**: `GET /v1/probe`, `POST /v1/verify` (returns only verified + message). [MCP server](docs/AGENT_VERIFICATION.md#mcp-server-for-safe-checkups) for humans and agent-to-agent checkups. See [docs/AGENT_VERIFICATION.md](docs/AGENT_VERIFICATION.md). |
| **Tests** | `pytest tests/` — schema validation, statistics, API endpoints, pipeline pre-filter. |

---

## Quick start

### 1. Environment

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. LLM setup (Ollama — default, open source)

TAOTF uses **Ollama** by default for all LLM calls (classification, verification). No API key needed.

```bash
# Install Ollama: https://ollama.com
ollama pull qwen2.5
# Ollama serves at http://localhost:11434 — TAOTF connects automatically.
```

To use OpenAI instead:
```bash
# In .env:
TAOTF_LLM_BACKEND=openai
OPENAI_API_KEY=sk-...
```

See `.env.example` for all configuration options.

### 3. Run the pipeline (raw wishes → signals)

```bash
# Put your wishes in wishes.xlsx (columns: id, wish_text)
python index.py
```

Produces:
- `taotf_signals.jsonl` — one JSON object per line (live append; resume-safe).
- `taotf_signals.xlsx` — full report with sheets: All Signals, Valid Signals, Pillar Summary, Signal Types, Beneficiary, Top Themes.

### 4. Normalize existing data (one-time)

If you have signals from an earlier run with non-canonical pillar names:
```bash
python scripts/normalize_existing_data.py
```

### 5. Run the API

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

- **Docs:** http://localhost:8000/docs
- **Stats:** http://localhost:8000/v1/stats
- **Signals:** http://localhost:8000/v1/signals?limit=20&quality=valid
- **Data quality:** http://localhost:8000/v1/data-quality

### 6. Run tests

```bash
pytest tests/ -v
```

**Examples:** See [docs/EXAMPLES.md](docs/EXAMPLES.md) for curl, Python, pipeline, ADI, and verification examples.

---

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health + project info |
| GET | `/v1/signals` | Paginated signals (filter: `quality`, `pillar`, `beneficiary`, `emotional_valence`) |
| GET | `/v1/stats` | Aggregate stats with bootstrap CIs on pillar distributions |
| GET | `/v1/pillars` | Pillar distribution |
| GET | `/v1/themes` | Top themes |
| GET | `/v1/intentions` | Agent-optimized summary of human aspiration |
| GET | `/v1/probe` | Agent verification: get a dynamic probe (question) |
| GET | `/v1/data-quality` | Schema conformance report |
| GET | `/v1/export` | Export signals as CSV or JSON |
| GET | `/v1/community-profile` | Cross-tabulation by pillar or beneficiary |
| POST | `/v1/compare` | Human vs agent: submit pre-tagged signals; get divergence with CIs, p-values, and alignment score |
| POST | `/v1/verify` | Agent verification: submit response; returns `verified` + `message` + `disclaimer` |
| POST | `/v1/contribute` | Submit a future intention |
| POST | `/v1/reload` | Reload signals from disk |

---

## TAOTF pillars & signal types

**Pillars (10):** Health & Longevity · Home & Living · Education & Knowledge · Energy & Sustainability · Space & Exploration · Nation & Society · Environment & Planet · Human Connection · Digital Identity · Human-AI Collaboration

**Signal types (5):** protective_aspiration · access_aspiration · transformation_aspiration · connection_aspiration · self_directed_aspiration

**Emotional valence (7):** hope · longing · urgency · gratitude · grief · joy · neutral

**Beneficiary (5):** self · family · community · humanity · unknown

---

## Agentic AI — Intentions & Alignment

TAOTF is a **structured human aspiration dataset**. For agentic AI this enables:

1. **Steer agents:** `GET /v1/intentions` returns a compact summary of "what humans want."
2. **Compare humans vs robots:** `POST /v1/compare` accepts pre-tagged aspiration signals. The API returns per-dimension divergence with 95% bootstrap CIs, p-values, and a single **aspiration_alignment_score**.
3. **Reproducible comparison:** Run the standalone **Aspiration Divergence Index (ADI)** script:
   ```bash
   python scripts/aspiration_divergence.py --human taotf_signals.jsonl --agent agent_wishes.jsonl -o report.json
   ```

See [docs/AGENTIC_AI.md](docs/AGENTIC_AI.md) for methodology, use cases, and citation.

---

**Limitation — can be gamed:** An agent can achieve a high aspiration_alignment_score by *stating* aspirations that match the human distribution (e.g. by querying `/v1/intentions` and outputting tags that mirror it). TAOTF measures **distributional similarity of stated aspirations**, not whether the agent genuinely holds those goals or will act on them. Use as one signal among many (e.g. with behavioral or outcome-based checks), not as a sole alignment or safety guarantee.

### Agent verification (dynamic)

To check agent behavior using probes that change each time:

1. **GET /v1/probe** — Returns a dynamic question (deterministic from an optional seed).
2. Send that prompt to the **agent under test**; collect its response.
3. **POST /v1/verify** — Submit the response. The server tags it, compares to human reference, and returns **verified** (bool) + **message** + **disclaimer**.
4. **MCP server** (`python mcp_server.py`) exposes tools for humans or agents to run this flow.

See [docs/AGENT_VERIFICATION.md](docs/AGENT_VERIFICATION.md).

---

## Limitations

- **Limited collection sites:** Initial data is from the Omnia Experience Center in Sohar, Oman (expanding to more cities) — not representative of global populations.
- **LLM-dependent classification:** Accuracy depends on the LLM model. The initial run with GPT-4o-mini produced 38 pillar names instead of 10, requiring normalization. No inter-annotator agreement has been measured.
- **Stated aspirations only:** Measures what people *say* they want, not their actual priorities or behavior.
- **Verification is not security:** The probe/verify flow checks distributional similarity, not genuine alignment. The scoring formula is in the source code.
- **Arbitrary equal weighting:** The alignment score weights 4 dimensions equally — this is a methodological choice, not a proven optimal weighting.
- **Self-selected participants:** Only visitors who chose to write wishes are represented.

## Data governance

- **Full anonymization** — no PII stored; collective signal mapping over individual profiling.
- **Zero data resale** — data is for research and the archive.
- **Long-term archival commitment** — structured for longitudinal civilization tracking.

Dataset license: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (see [docs/DATASET.md](docs/DATASET.md)). Code: [MIT](LICENSE).

---


**Humans are not only consumers of the future. They are co-authors of it.**

**By [Vivid Studio](https://vividstudio.me)**
