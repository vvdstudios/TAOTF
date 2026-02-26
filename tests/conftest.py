"""Shared test fixtures for TAOTF tests."""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


SAMPLE_VALID_SIGNAL = {
    "wish_id": "test-001",
    "translated": "I wish for a better education",
    "quality": "valid",
    "primary_pillar": "Education & Knowledge",
    "secondary_pillars": [],
    "primary_pillar_confidence": 0.9,
    "signal_type": "self_directed_aspiration",
    "beneficiary": "self",
    "emotional_valence": "hope",
    "urgency_score": 0.5,
    "time_horizon": "near_term",
    "key_themes": ["education", "learning"],
    "_raw_text": "I wish for better education",
    "_written_at": "2026-01-01T00:00:00",
}

SAMPLE_NOISE_SIGNAL = {
    "wish_id": "test-002",
    "translated": None,
    "quality": "noise",
    "primary_pillar": "",
    "secondary_pillars": [],
    "primary_pillar_confidence": 0.0,
    "signal_type": "",
    "beneficiary": "",
    "emotional_valence": "",
    "urgency_score": 0.0,
    "time_horizon": "",
    "key_themes": [],
    "_raw_text": "asdf",
    "_written_at": "2026-01-01T00:00:00",
}

SAMPLE_NON_CANONICAL_SIGNAL = {
    "wish_id": "test-003",
    "translated": "I wish for wealth",
    "quality": "valid",
    "primary_pillar": "Economy & Prosperity",
    "secondary_pillars": [],
    "primary_pillar_confidence": 0.8,
    "signal_type": "community_aspiration",
    "beneficiary": "community",
    "emotional_valence": "hope",
    "urgency_score": 0.3,
    "time_horizon": "long_term",
    "key_themes": ["wealth", "prosperity"],
    "_raw_text": "I wish for wealth",
    "_written_at": "2026-01-01T00:00:00",
}


def make_diverse_signals(n: int = 20) -> list[dict]:
    """Generate a diverse set of valid signals for testing."""
    pillars = [
        "Education & Knowledge", "Human Connection", "Nation & Society",
        "Health & Longevity", "Home & Living", "Space & Exploration",
        "Digital Identity", "Environment & Planet", "Human-AI Collaboration",
        "Energy & Sustainability",
    ]
    types = [
        "self_directed_aspiration", "connection_aspiration",
        "transformation_aspiration", "access_aspiration", "protective_aspiration",
    ]
    beneficiaries = ["self", "family", "community", "humanity", "unknown"]
    valences = ["hope", "longing", "urgency", "joy", "neutral", "gratitude", "grief"]

    signals = []
    for i in range(n):
        signals.append({
            "wish_id": f"diverse-{i:04d}",
            "translated": f"Test wish {i}",
            "quality": "valid",
            "primary_pillar": pillars[i % len(pillars)],
            "secondary_pillars": [],
            "primary_pillar_confidence": 0.8,
            "signal_type": types[i % len(types)],
            "beneficiary": beneficiaries[i % len(beneficiaries)],
            "emotional_valence": valences[i % len(valences)],
            "urgency_score": 0.5,
            "time_horizon": "near_term",
            "key_themes": ["test"],
            "_raw_text": f"Test wish {i}",
            "_written_at": "2026-01-01T00:00:00",
        })
    return signals


@pytest.fixture
def sample_signal():
    return dict(SAMPLE_VALID_SIGNAL)


@pytest.fixture
def sample_signals():
    return make_diverse_signals(20)


@pytest.fixture
def temp_jsonl(sample_signals):
    """Create a temporary JSONL file with sample signals."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for s in sample_signals:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
        # Add a noise signal
        f.write(json.dumps(SAMPLE_NOISE_SIGNAL, ensure_ascii=False) + "\n")
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def temp_signals_dir(sample_signals):
    """Create a temporary directory with a signals JSONL file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_path = Path(tmpdir) / "taotf_signals.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for s in sample_signals:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
            f.write(json.dumps(SAMPLE_NOISE_SIGNAL, ensure_ascii=False) + "\n")
        yield tmpdir
