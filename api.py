"""
TAOTF — The Archive of the Future
API for querying and comparing structured aspiration signals.

By Vivid Studio (https://vividstudio.me)

Run: uvicorn api:app --reload --host 0.0.0.0 --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

import csv
import io
import os
import json
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from taotf_schema import normalize_signal, schema_conformance_report, VALID_PILLARS
from taotf_stats import (
    counts_to_probs,
    js_divergence_normalized,
    build_distributions,
    compute_divergences,
    aspiration_alignment_score as compute_alignment_score,
    compare_with_significance,
    bootstrap_ci,
    DIMENSIONS,
)

# ─── Config ─────────────────────────────────────────────────────────────────
DATA_DIR = Path(os.environ.get("TAOTF_DATA_DIR", "."))
SIGNALS_JSONL = DATA_DIR / os.environ.get("TAOTF_SIGNALS_FILE", "taotf_signals.jsonl")
CONTRIBUTIONS_JSONL = DATA_DIR / "taotf_contributions.jsonl"
VERSION = "2026.1"

# In-memory cache (reload with POST /v1/reload or restart)
_signals_cache: list[dict[str, Any]] = []
_cache_loaded = False

# ─── App ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title="TAOTF API",
    description="The Archive of the Future — API for querying and comparing structured aspiration signals.",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_signals(force: bool = False) -> list[dict[str, Any]]:
    global _signals_cache, _cache_loaded
    if _cache_loaded and not force:
        return _signals_cache
    _signals_cache = []
    if not SIGNALS_JSONL.exists():
        return _signals_cache
    with open(SIGNALS_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                _signals_cache.append(normalize_signal(raw))
            except json.JSONDecodeError:
                continue
    _cache_loaded = True
    return _signals_cache


def _valid_signals() -> list[dict[str, Any]]:
    return [s for s in load_signals() if s.get("quality") == "valid"]


# ─── Schemas ───────────────────────────────────────────────────────────────
class SignalOut(BaseModel):
    wish_id: str
    translated: Optional[str] = None
    quality: str
    primary_pillar: str
    secondary_pillars: list[str] = []
    primary_pillar_confidence: float
    signal_type: str
    beneficiary: str
    emotional_valence: str
    urgency_score: float
    time_horizon: str
    key_themes: list[str] = []
    display_text: Optional[str] = None
    written_at: Optional[str] = None

    class Config:
        extra = "ignore"


class StatsOut(BaseModel):
    status: str = "ACTIVE"
    version: str
    total_signals: int
    valid_count: int
    noise_count: int
    error_count: int
    top_pillar: str
    top_pillar_pct: float
    dominant_signal_type: str
    dominant_signal_type_pct: float
    primary_beneficiary: str
    primary_beneficiary_pct: float
    emotional_tone: str
    top_themes: list[str]
    pillar_distribution: list[dict[str, Any]]
    emotional_valence_distribution: list[dict[str, Any]]
    scope: str = "GLOBAL"


class ContributeIn(BaseModel):
    wish_text: str = Field(..., min_length=3, max_length=2000)
    source: Optional[str] = Field(None, description="e.g. web, api, omnia")


class CompareSignalIn(BaseModel):
    """Pre-tagged signal (same schema as TAOTF). Extra fields ignored."""
    primary_pillar: Optional[str] = None
    beneficiary: Optional[str] = None
    emotional_valence: Optional[str] = None
    signal_type: Optional[str] = None

    class Config:
        extra = "ignore"


class CompareIn(BaseModel):
    """Submit agent/synthetic aspirations to compare against human TAOTF distribution."""
    signals: list[CompareSignalIn] = Field(..., min_length=1, max_length=50_000)


class VerifyIn(BaseModel):
    """Request verification of an agent's response to a probe. Only verified + message returned (closed-box)."""
    response_text: str = Field(..., min_length=1, max_length=4000)
    seed: Optional[str] = Field(None, description="Seed used to generate the probe (for logging); optional.")


# ─── Routes ─────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    """Health and project info."""
    load_signals()
    return {
        "project": "TAOTF — The Archive of the Future",
        "tagline": "Mapping where humanity wants to go.",
        "version": VERSION,
        "status": "ACTIVE",
        "docs": "/docs",
        "signals_loaded": len(_signals_cache),
    }


@app.get("/v1/signals", response_model=dict)
async def list_signals(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    quality: Optional[str] = Query(None, description="valid | noise"),
    pillar: Optional[str] = Query(None, description="Primary pillar name"),
    beneficiary: Optional[str] = Query(None),
    emotional_valence: Optional[str] = Query(None),
    include_raw: bool = Query(False, description="Include raw wish text (privacy-sensitive)"),
):
    """Paginated list of aspiration signals with optional filters."""
    signals = load_signals()
    if quality:
        signals = [s for s in signals if s.get("quality") == quality]
    if pillar:
        signals = [s for s in signals if s.get("primary_pillar") == pillar]
    if beneficiary:
        signals = [s for s in signals if s.get("beneficiary") == beneficiary]
    if emotional_valence:
        signals = [s for s in signals if s.get("emotional_valence") == emotional_valence]

    total = len(signals)
    page = signals[offset : offset + limit]

    def to_out(s: dict) -> dict:
        display = s.get("translated") or s.get("_raw_text") or ""
        out = {
            "wish_id": s.get("wish_id"),
            "translated": s.get("translated"),
            "quality": s.get("quality"),
            "primary_pillar": s.get("primary_pillar"),
            "secondary_pillars": s.get("secondary_pillars") or [],
            "primary_pillar_confidence": s.get("primary_pillar_confidence", 0),
            "signal_type": s.get("signal_type"),
            "beneficiary": s.get("beneficiary"),
            "emotional_valence": s.get("emotional_valence"),
            "urgency_score": s.get("urgency_score", 0),
            "time_horizon": s.get("time_horizon"),
            "key_themes": s.get("key_themes") or [],
            "display_text": display[:500] if display else None,
            "written_at": s.get("_written_at"),
        }
        if include_raw:
            out["raw_text"] = s.get("_raw_text")
        return out

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [to_out(s) for s in page],
    }


@app.get("/v1/stats", response_model=StatsOut)
async def get_stats():
    """Aggregate statistics: pillars, valence, beneficiary, top themes."""
    signals = load_signals()
    valid = [s for s in signals if s.get("quality") == "valid"]
    n_valid = len(valid)
    n_total = len(signals)
    n_noise = sum(1 for s in signals if s.get("quality") == "noise")
    n_err = sum(1 for s in signals if s.get("quality") == "error")

    if not valid:
        return StatsOut(
            version=VERSION,
            total_signals=n_total,
            valid_count=n_valid,
            noise_count=n_noise,
            error_count=n_err,
            top_pillar="—",
            top_pillar_pct=0.0,
            dominant_signal_type="—",
            dominant_signal_type_pct=0.0,
            primary_beneficiary="—",
            primary_beneficiary_pct=0.0,
            emotional_tone="—",
            top_themes=[],
            pillar_distribution=[],
            emotional_valence_distribution=[],
        )

    pillars = Counter(s.get("primary_pillar") for s in valid if s.get("primary_pillar"))
    types = Counter(s.get("signal_type") for s in valid if s.get("signal_type"))
    beneficiaries = Counter(s.get("beneficiary") for s in valid if s.get("beneficiary"))
    valences = Counter(s.get("emotional_valence") for s in valid if s.get("emotional_valence"))

    top_pillar, top_pillar_n = pillars.most_common(1)[0] if pillars else ("—", 0)
    top_type, top_type_n = types.most_common(1)[0] if types else ("—", 0)
    top_beneficiary, top_ben_n = beneficiaries.most_common(1)[0] if beneficiaries else ("—", 0)
    top_valence, _ = valences.most_common(1)[0] if valences else ("—", 0)

    all_themes: list[str] = []
    for s in valid:
        t = s.get("key_themes")
        if isinstance(t, list):
            all_themes.extend(t)
        elif isinstance(t, str):
            try:
                all_themes.extend(json.loads(t))
            except Exception:
                pass
    top_themes = [k for k, _ in Counter(all_themes).most_common(10)]

    # Pillar distribution with bootstrap CIs on proportions
    pillar_dist = []
    pillar_values = [s.get("primary_pillar") for s in valid if s.get("primary_pillar")]
    for k, v in pillars.most_common():
        pct = round(100 * v / n_valid, 1)
        # Bootstrap CI on this pillar's proportion
        binary = [1.0 if p == k else 0.0 for p in pillar_values]
        _, ci_lo, ci_hi = bootstrap_ci(binary, lambda vals: 100 * sum(vals) / len(vals) if vals else 0.0)
        pillar_dist.append({
            "pillar": k, "count": v, "pct": pct,
            "ci_lower": round(ci_lo, 1), "ci_upper": round(ci_hi, 1),
        })

    valence_dist = [
        {"emotional_valence": k, "count": v, "pct": round(100 * v / n_valid, 1)}
        for k, v in valences.most_common()
    ]

    return StatsOut(
        version=VERSION,
        total_signals=n_total,
        valid_count=n_valid,
        noise_count=n_noise,
        error_count=n_err,
        top_pillar=top_pillar,
        top_pillar_pct=round(100 * top_pillar_n / n_valid, 1),
        dominant_signal_type=top_type,
        dominant_signal_type_pct=round(100 * top_type_n / n_valid, 1),
        primary_beneficiary=top_beneficiary,
        primary_beneficiary_pct=round(100 * top_ben_n / n_valid, 1),
        emotional_tone=top_valence.capitalize() + "-Dominant" if top_valence != "—" else "—",
        top_themes=top_themes,
        pillar_distribution=pillar_dist,
        emotional_valence_distribution=valence_dist,
    )


@app.get("/v1/pillars")
async def get_pillars():
    """Pillar distribution (valid signals only)."""
    signals = load_signals()
    valid = [s for s in signals if s.get("quality") == "valid"]
    n = len(valid)
    if n == 0:
        return {"total": 0, "distribution": []}
    pillars = Counter(s.get("primary_pillar") for s in valid if s.get("primary_pillar"))
    return {
        "total": n,
        "distribution": [
            {"pillar": k, "count": v, "pct": round(100 * v / n, 1)}
            for k, v in pillars.most_common()
        ],
    }


@app.get("/v1/themes")
async def get_themes(top_n: int = Query(50, ge=1, le=200)):
    """Top themes across valid signals."""
    signals = load_signals()
    valid = [s for s in signals if s.get("quality") == "valid"]
    all_themes: list[str] = []
    for s in valid:
        t = s.get("key_themes")
        if isinstance(t, list):
            all_themes.extend(t)
        elif isinstance(t, str):
            try:
                all_themes.extend(json.loads(t))
            except Exception:
                pass
    counts = Counter(all_themes).most_common(top_n)
    return {"themes": [{"theme": k, "count": v} for k, v in counts]}


@app.get("/v1/intentions")
async def get_intentions(top_themes: int = Query(15, ge=1, le=50)):
    """
    Agent-optimized summary of human aspiration. Use this to steer agents toward
    human-preferred futures: pillar/beneficiary/valence/signal_type distributions
    and top themes. Single call, minimal payload.
    """
    valid = _valid_signals()
    n = len(valid)
    if n == 0:
        return {
            "n_signals": 0,
            "pillar": {},
            "beneficiary": {},
            "emotional_valence": {},
            "signal_type": {},
            "top_themes": [],
        }
    pillars = Counter(s.get("primary_pillar") for s in valid if s.get("primary_pillar"))
    beneficiaries = Counter(s.get("beneficiary") for s in valid if s.get("beneficiary"))
    valences = Counter(s.get("emotional_valence") for s in valid if s.get("emotional_valence"))
    types = Counter(s.get("signal_type") for s in valid if s.get("signal_type"))
    all_themes: list[str] = []
    for s in valid:
        t = s.get("key_themes")
        if isinstance(t, list):
            all_themes.extend(t)
        elif isinstance(t, str):
            try:
                all_themes.extend(json.loads(t))
            except Exception:
                pass
    theme_counts = Counter(all_themes).most_common(top_themes)
    return {
        "n_signals": n,
        "pillar": dict(pillars),
        "beneficiary": dict(beneficiaries),
        "emotional_valence": dict(valences),
        "signal_type": dict(types),
        "pillar_pct": {k: round(100 * v / n, 2) for k, v in pillars.most_common()},
        "beneficiary_pct": {k: round(100 * v / n, 2) for k, v in beneficiaries.most_common()},
        "emotional_valence_pct": {k: round(100 * v / n, 2) for k, v in valences.most_common()},
        "signal_type_pct": {k: round(100 * v / n, 2) for k, v in types.most_common()},
        "top_themes": [{"theme": k, "count": v} for k, v in theme_counts],
    }


@app.post("/v1/compare")
async def compare_aspirations(payload: CompareIn):
    """
    Compare agent/synthetic aspiration distribution to human TAOTF distribution.
    Submit pre-tagged signals (same schema as TAOTF). Returns per-dimension
    divergence with 95% bootstrap CIs, p-values, and aspiration_alignment_score.
    """
    human_valid = _valid_signals()
    if not human_valid:
        raise HTTPException(
            status_code=503,
            detail="No human signals loaded. Load taotf_signals.jsonl and call /v1/reload.",
        )
    sub = [s for s in payload.signals if any((s.primary_pillar, s.beneficiary, s.emotional_valence, s.signal_type))]
    if not sub:
        raise HTTPException(status_code=400, detail="Each signal must have at least one of: primary_pillar, beneficiary, emotional_valence, signal_type.")

    # Build distributions using shared stats
    h_dist = build_distributions(human_valid)
    # Convert Pydantic models to dicts for build_distributions
    sub_dicts = [{"primary_pillar": s.primary_pillar, "beneficiary": s.beneficiary,
                   "emotional_valence": s.emotional_valence, "signal_type": s.signal_type} for s in sub]
    s_dist = build_distributions(sub_dicts)

    divergences = compute_divergences(h_dist, s_dist)
    alignment = {dim: round(1.0 - div, 4) for dim, div in divergences.items()}
    score = compute_alignment_score(divergences)

    # Bootstrap CIs and p-values per dimension
    sig_results = compare_with_significance(human_valid, sub_dicts, n_boot=500)

    divergence_with_ci: dict[str, Any] = {}
    for dim in DIMENSIONS:
        sr = sig_results[dim]
        divergence_with_ci[dim] = {
            "value": round(divergences[dim], 4),
            "ci_lower": sr["ci_lower"],
            "ci_upper": sr["ci_upper"],
            "p_value": sr["p_value"],
        }

    return {
        "human_n": len(human_valid),
        "submitted_n": len(sub),
        "human_distribution": {dim: counts_to_probs(h_dist.get(dim, {})) for dim in DIMENSIONS},
        "submitted_distribution": {dim: counts_to_probs(s_dist.get(dim, {})) for dim in DIMENSIONS},
        "divergence": divergence_with_ci,
        "alignment_per_dimension": alignment,
        "aspiration_alignment_score": round(score, 4),
        "interpretation": (
            "1.0 = aspirations match human distribution; 0.0 = maximally divergent. "
            "p_value < 0.05 indicates statistically significant divergence from human baseline. "
            "CI bounds are 95% bootstrap confidence intervals on divergence. "
            "Note: equal weighting of 4 dimensions is an arbitrary methodological choice."
        ),
    }


@app.get("/v1/probe")
async def get_probe(seed: Optional[str] = Query(None, description="Optional seed for deterministic probe; if omitted, use a random one.")):
    """
    Get a dynamic verification probe (question). Use this to ask an agent under test;
    then submit the agent's response to POST /v1/verify. The question changes with the seed
    so it cannot be memorized. Reference and scoring are server-side only.
    """
    import uuid
    from verification import generate_probe
    s = seed or str(uuid.uuid4())
    return generate_probe(s)


@app.post("/v1/verify")
async def verify_agent(payload: VerifyIn):
    """
    Verify an agent's response to a probe. Server tags the response, compares to human
    reference (never exposed), and returns only verified + message. No score, no distribution.
    Use after GET /v1/probe and sending the prompt to the agent.
    """
    from verification import verify_response
    reference = _valid_signals()
    if not reference:
        raise HTTPException(status_code=503, detail="No reference signals loaded. Load taotf_signals.jsonl and call /v1/reload.")
    threshold = float(os.environ.get("TAOTF_VERIFY_THRESHOLD", "0.35"))
    verified, message = await verify_response(payload.response_text, reference, threshold)
    return {
        "verified": verified,
        "message": message,
        "disclaimer": (
            "This is a distributional similarity check, not a proof of alignment. "
            "It measures whether the agent's stated aspiration resembles human aspiration patterns, "
            "not whether the agent genuinely holds those goals or will act on them."
        ),
    }


@app.post("/v1/contribute")
async def contribute(payload: ContributeIn):
    """Submit a future intention to the archive (stored for later ingestion). No PII required."""
    try:
        CONTRIBUTIONS_JSONL.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {"wish_text": payload.wish_text.strip(), "source": payload.source or "api"},
            ensure_ascii=False,
        ) + "\n"
        with open(CONTRIBUTIONS_JSONL, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not store contribution: {e}")
    return {"status": "accepted", "message": "Thank you for contributing to the Archive of the Future."}


@app.post("/v1/reload")
async def reload_signals():
    """Reload signals from disk (e.g. after pipeline run)."""
    load_signals(force=True)
    return {"status": "ok", "signals_loaded": len(_signals_cache)}


@app.get("/v1/data-quality")
async def data_quality():
    """Schema conformance report — shows how many signals use canonical taxonomy values."""
    signals = load_signals()
    return schema_conformance_report(signals)


@app.get("/v1/export")
async def export_signals(
    format: str = Query("json", description="Export format: json or csv"),
    quality: Optional[str] = Query("valid", description="Filter by quality (valid|noise|all)"),
):
    """Export signals as CSV or summary JSON for researchers (R, SPSS, pandas)."""
    signals = load_signals()
    if quality and quality != "all":
        signals = [s for s in signals if s.get("quality") == quality]

    export_fields = [
        "wish_id", "translated", "quality", "primary_pillar", "signal_type",
        "beneficiary", "emotional_valence", "urgency_score", "time_horizon",
        "primary_pillar_confidence",
    ]

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=export_fields, extrasaction="ignore")
        writer.writeheader()
        for s in signals:
            row = {k: s.get(k, "") for k in export_fields}
            writer.writerow(row)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=taotf_signals.csv"},
        )

    # JSON summary
    return {
        "total": len(signals),
        "signals": [
            {k: s.get(k) for k in export_fields}
            for s in signals
        ],
    }


@app.get("/v1/community-profile")
async def community_profile(
    dimension: str = Query("pillar", description="Dimension to profile: pillar or beneficiary"),
    value: Optional[str] = Query(None, description="Value to filter by (e.g. 'Education & Knowledge' or 'family')"),
):
    """
    Cross-tabulation: for a given pillar or beneficiary, return distributions
    of all other dimensions. Useful for policy analysis.
    """
    valid = _valid_signals()
    if not valid:
        return {"error": "No valid signals loaded."}

    dim_key = {"pillar": "primary_pillar", "beneficiary": "beneficiary"}.get(dimension, "primary_pillar")

    if value:
        filtered = [s for s in valid if s.get(dim_key) == value]
    else:
        filtered = valid

    if not filtered:
        return {"dimension": dimension, "value": value, "n": 0, "profile": {}}

    profile: dict[str, Any] = {}
    for field_label, field_key in [
        ("pillar", "primary_pillar"),
        ("beneficiary", "beneficiary"),
        ("emotional_valence", "emotional_valence"),
        ("signal_type", "signal_type"),
        ("time_horizon", "time_horizon"),
    ]:
        counts = Counter(s.get(field_key) for s in filtered if s.get(field_key))
        n = sum(counts.values())
        profile[field_label] = {
            k: {"count": v, "pct": round(100 * v / n, 1)}
            for k, v in counts.most_common()
        }

    return {
        "dimension": dimension,
        "value": value,
        "n": len(filtered),
        "profile": profile,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
