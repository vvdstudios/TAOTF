"""Tests for taotf_schema.py — taxonomy normalization and validation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from taotf_schema import (
    VALID_PILLARS,
    VALID_SIGNAL_TYPES,
    VALID_BENEFICIARIES,
    VALID_VALENCES,
    VALID_TIME_HORIZONS,
    PILLAR_NORMALIZATION,
    SIGNAL_TYPE_NORMALIZATION,
    normalize_pillar,
    normalize_signal_type,
    normalize_signal,
    validate_signal,
    schema_conformance_report,
)
from conftest import SAMPLE_VALID_SIGNAL, SAMPLE_NON_CANONICAL_SIGNAL, SAMPLE_NOISE_SIGNAL


class TestCanonicalSets:
    def test_10_pillars(self):
        assert len(VALID_PILLARS) == 10

    def test_5_signal_types(self):
        assert len(VALID_SIGNAL_TYPES) == 5

    def test_5_beneficiaries(self):
        assert len(VALID_BENEFICIARIES) == 5

    def test_7_valences(self):
        assert len(VALID_VALENCES) == 7

    def test_4_time_horizons(self):
        assert len(VALID_TIME_HORIZONS) == 4


class TestPillarNormalization:
    """Test that all 38 observed pillar variants map to canonical pillars."""

    def test_canonical_pillars_unchanged(self):
        for pillar in VALID_PILLARS:
            assert normalize_pillar(pillar) == pillar

    def test_economy_variants_to_nation_society(self):
        variants = [
            "Economy & Prosperity",
            "Economy & Wealth",
            "Economic Prosperity",
            "Economy & Society",
            "Economy & Innovation",
            "Finance & Economy",
        ]
        for v in variants:
            assert normalize_pillar(v) == "Nation & Society", f"{v} should map to Nation & Society"

    def test_family_variants_to_home_living(self):
        variants = [
            "Family & Living",
            "Family & Relationships",
            "Family",
            "Family & Society",
            "Work & Life Balance",
        ]
        for v in variants:
            assert normalize_pillar(v) == "Home & Living", f"{v} should map to Home & Living"

    def test_self_development_to_education(self):
        variants = ["Self-Development", "Self-Directed", "Self-Directed Aspiration"]
        for v in variants:
            assert normalize_pillar(v) == "Education & Knowledge"

    def test_signal_type_leak_to_education(self):
        assert normalize_pillar("self_directed_aspiration") == "Education & Knowledge"
        assert normalize_pillar("access_aspiration") == "Education & Knowledge"

    def test_spirituality_to_human_connection(self):
        for v in ["Spirituality", "Spirituality & Beliefs", "spirituality"]:
            assert normalize_pillar(v) == "Human Connection"

    def test_transport_to_space(self):
        for v in ["Transportation", "Mobility & Transportation", "Travel & Adventure"]:
            assert normalize_pillar(v) == "Space & Exploration"

    def test_arts_to_human_connection(self):
        for v in ["Culture & Arts", "Entertainment & Arts", "Entertainment & Leisure"]:
            assert normalize_pillar(v) == "Human Connection"

    def test_all_normalization_targets_are_canonical(self):
        for source, target in PILLAR_NORMALIZATION.items():
            assert target in VALID_PILLARS, f"Normalization target '{target}' for '{source}' is not canonical"

    def test_none_and_empty(self):
        assert normalize_pillar(None) == "Nation & Society"
        assert normalize_pillar("") == "Nation & Society"


class TestSignalTypeNormalization:
    def test_canonical_unchanged(self):
        for st in VALID_SIGNAL_TYPES:
            assert normalize_signal_type(st) == st

    def test_community_aspiration(self):
        assert normalize_signal_type("community_aspiration") == "connection_aspiration"

    def test_hope_aspiration(self):
        assert normalize_signal_type("hope_aspiration") == "self_directed_aspiration"

    def test_all_targets_are_canonical(self):
        for source, target in SIGNAL_TYPE_NORMALIZATION.items():
            assert target in VALID_SIGNAL_TYPES


class TestNormalizeSignal:
    def test_valid_signal_unchanged(self):
        result = normalize_signal(SAMPLE_VALID_SIGNAL)
        assert result["primary_pillar"] == "Education & Knowledge"
        assert result["signal_type"] == "self_directed_aspiration"

    def test_non_canonical_normalized(self):
        result = normalize_signal(SAMPLE_NON_CANONICAL_SIGNAL)
        assert result["primary_pillar"] == "Nation & Society"
        assert result["signal_type"] == "connection_aspiration"

    def test_noise_signal_not_normalized(self):
        result = normalize_signal(SAMPLE_NOISE_SIGNAL)
        assert result["quality"] == "noise"
        # Noise signals keep their original values
        assert result["primary_pillar"] == ""

    def test_returns_new_dict(self):
        original = dict(SAMPLE_NON_CANONICAL_SIGNAL)
        result = normalize_signal(original)
        assert result is not original
        assert original["primary_pillar"] == "Economy & Prosperity"  # unchanged


class TestValidateSignal:
    def test_valid_canonical_signal(self):
        is_valid, issues = validate_signal(SAMPLE_VALID_SIGNAL)
        assert is_valid
        assert issues == []

    def test_non_canonical_signal_fails(self):
        is_valid, issues = validate_signal(SAMPLE_NON_CANONICAL_SIGNAL)
        assert not is_valid
        assert len(issues) >= 1
        assert any("primary_pillar" in i for i in issues)

    def test_noise_signal_passes(self):
        is_valid, issues = validate_signal(SAMPLE_NOISE_SIGNAL)
        assert is_valid


class TestSchemaConformanceReport:
    def test_all_canonical(self):
        signals = [SAMPLE_VALID_SIGNAL] * 10
        report = schema_conformance_report(signals)
        assert report["conforming"] == 10
        assert report["non_conforming"] == 0
        assert report["conformance_pct"] == 100.0

    def test_mixed_signals(self):
        signals = [SAMPLE_VALID_SIGNAL] * 8 + [SAMPLE_NON_CANONICAL_SIGNAL] * 2
        report = schema_conformance_report(signals)
        assert report["conforming"] == 8
        assert report["non_conforming"] == 2
        assert report["conformance_pct"] == 80.0
        assert "primary_pillar" in report["non_canonical_values"]

    def test_with_noise(self):
        signals = [SAMPLE_VALID_SIGNAL, SAMPLE_NOISE_SIGNAL]
        report = schema_conformance_report(signals)
        assert report["total_signals"] == 2
        assert report["valid_signals"] == 1
        assert report["conforming"] == 1
