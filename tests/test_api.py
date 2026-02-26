"""Tests for api.py — FastAPI endpoints."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from conftest import make_diverse_signals, SAMPLE_NOISE_SIGNAL


@pytest.fixture
def client(temp_signals_dir):
    """Create a test client with signals loaded from temp directory."""
    os.environ["TAOTF_DATA_DIR"] = temp_signals_dir
    os.environ["TAOTF_SIGNALS_FILE"] = "taotf_signals.jsonl"

    # Force reimport to pick up new env vars
    import importlib
    import api as api_module
    importlib.reload(api_module)

    # Reset cache
    api_module._signals_cache = []
    api_module._cache_loaded = False
    api_module.SIGNALS_JSONL = Path(temp_signals_dir) / "taotf_signals.jsonl"

    with TestClient(api_module.app) as c:
        yield c


class TestRoot:
    def test_root_returns_project_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"] == "TAOTF — The Archive of the Future"
        assert data["status"] == "ACTIVE"
        assert data["signals_loaded"] > 0


class TestSignals:
    def test_list_signals(self, client):
        resp = client.get("/v1/signals?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "data" in data
        assert len(data["data"]) <= 5

    def test_filter_by_quality(self, client):
        resp = client.get("/v1/signals?quality=valid")
        assert resp.status_code == 200
        data = resp.json()
        for s in data["data"]:
            assert s["quality"] == "valid"

    def test_pagination(self, client):
        resp1 = client.get("/v1/signals?limit=5&offset=0")
        resp2 = client.get("/v1/signals?limit=5&offset=5")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        ids1 = {s["wish_id"] for s in resp1.json()["data"]}
        ids2 = {s["wish_id"] for s in resp2.json()["data"]}
        assert ids1.isdisjoint(ids2)


class TestStats:
    def test_stats_returns_valid_data(self, client):
        resp = client.get("/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid_count"] > 0
        assert data["total_signals"] > 0
        assert "pillar_distribution" in data
        assert len(data["pillar_distribution"]) > 0

    def test_stats_pillar_dist_has_ci(self, client):
        resp = client.get("/v1/stats")
        data = resp.json()
        for entry in data["pillar_distribution"]:
            assert "ci_lower" in entry
            assert "ci_upper" in entry
            assert entry["ci_lower"] <= entry["pct"]
            assert entry["ci_upper"] >= entry["pct"]


class TestCompare:
    def test_compare_basic(self, client):
        payload = {
            "signals": [
                {"primary_pillar": "Education & Knowledge", "beneficiary": "self",
                 "emotional_valence": "hope", "signal_type": "self_directed_aspiration"},
                {"primary_pillar": "Human Connection", "beneficiary": "family",
                 "emotional_valence": "longing", "signal_type": "connection_aspiration"},
            ]
        }
        resp = client.post("/v1/compare", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "aspiration_alignment_score" in data
        assert 0.0 <= data["aspiration_alignment_score"] <= 1.0
        assert "divergence" in data
        # Check that divergence has CI and p-value
        for dim in ["pillar", "beneficiary", "emotional_valence", "signal_type"]:
            assert "ci_lower" in data["divergence"][dim]
            assert "p_value" in data["divergence"][dim]

    def test_compare_empty_signals_rejected(self, client):
        resp = client.post("/v1/compare", json={"signals": [{}]})
        assert resp.status_code == 400


class TestProbe:
    def test_probe_returns_prompt(self, client):
        resp = client.get("/v1/probe?seed=test123")
        assert resp.status_code == 200
        data = resp.json()
        assert "probe_id" in data
        assert "prompt" in data
        assert len(data["prompt"]) > 10

    def test_probe_deterministic(self, client):
        r1 = client.get("/v1/probe?seed=abc").json()
        r2 = client.get("/v1/probe?seed=abc").json()
        assert r1["prompt"] == r2["prompt"]
        assert r1["probe_id"] == r2["probe_id"]


class TestDataQuality:
    def test_data_quality_endpoint(self, client):
        resp = client.get("/v1/data-quality")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_signals" in data
        assert "conforming" in data
        assert "conformance_pct" in data


class TestExport:
    def test_export_json(self, client):
        resp = client.get("/v1/export?format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "signals" in data
        assert len(data["signals"]) > 0

    def test_export_csv(self, client):
        resp = client.get("/v1/export?format=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        lines = resp.text.strip().split("\n")
        assert len(lines) > 1  # header + data
        assert "wish_id" in lines[0]


class TestCommunityProfile:
    def test_profile_by_pillar(self, client):
        resp = client.get("/v1/community-profile?dimension=pillar&value=Education+%26+Knowledge")
        assert resp.status_code == 200
        data = resp.json()
        assert data["dimension"] == "pillar"
        assert "profile" in data

    def test_profile_all(self, client):
        resp = client.get("/v1/community-profile?dimension=pillar")
        assert resp.status_code == 200
        data = resp.json()
        assert data["n"] > 0


class TestContribute:
    def test_contribute(self, client):
        resp = client.post("/v1/contribute", json={"wish_text": "I wish for peace"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"


class TestReload:
    def test_reload(self, client):
        resp = client.post("/v1/reload")
        assert resp.status_code == 200
        assert resp.json()["signals_loaded"] > 0
