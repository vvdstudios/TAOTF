"""Tests for taotf_stats.py — JS divergence, distributions, bootstrap CI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from taotf_stats import (
    js_divergence_normalized,
    counts_to_probs,
    build_distributions,
    alignment_score,
    bootstrap_ci,
    compute_divergences,
    aspiration_alignment_score,
)
from conftest import SAMPLE_VALID_SIGNAL, make_diverse_signals


class TestJSDivergence:
    def test_identical_distributions_zero(self):
        p = {"a": 10, "b": 20, "c": 30}
        assert js_divergence_normalized(p, p) < 1e-10

    def test_disjoint_distributions_one(self):
        p = {"a": 100}
        q = {"b": 100}
        result = js_divergence_normalized(p, q)
        assert abs(result - 1.0) < 1e-10

    def test_symmetric(self):
        p = {"a": 10, "b": 20}
        q = {"a": 5, "b": 35}
        assert abs(js_divergence_normalized(p, q) - js_divergence_normalized(q, p)) < 1e-10

    def test_range_zero_to_one(self):
        p = {"a": 10, "b": 5, "c": 1}
        q = {"a": 1, "b": 5, "c": 10}
        result = js_divergence_normalized(p, q)
        assert 0.0 <= result <= 1.0

    def test_empty_distributions(self):
        assert js_divergence_normalized({}, {}) == 0.0

    def test_one_empty(self):
        # When q is empty, q_total is 1 (fallback), all Q values are 0.
        # JS divergence with one distribution having all mass and other having none = 0.5.
        p = {"a": 10}
        result = js_divergence_normalized(p, {})
        assert abs(result - 0.5) < 1e-10


class TestCountsToProbs:
    def test_basic(self):
        probs = counts_to_probs({"a": 1, "b": 3})
        assert abs(probs["a"] - 0.25) < 1e-10
        assert abs(probs["b"] - 0.75) < 1e-10

    def test_sums_to_one(self):
        probs = counts_to_probs({"x": 10, "y": 20, "z": 70})
        assert abs(sum(probs.values()) - 1.0) < 1e-10

    def test_empty(self):
        probs = counts_to_probs({})
        assert probs == {}


class TestBuildDistributions:
    def test_all_dimensions_present(self):
        signals = make_diverse_signals(10)
        dist = build_distributions(signals)
        assert "pillar" in dist
        assert "beneficiary" in dist
        assert "emotional_valence" in dist
        assert "signal_type" in dist

    def test_counts_are_correct(self):
        signals = [
            {"primary_pillar": "Education & Knowledge", "beneficiary": "self",
             "emotional_valence": "hope", "signal_type": "self_directed_aspiration"},
            {"primary_pillar": "Education & Knowledge", "beneficiary": "family",
             "emotional_valence": "hope", "signal_type": "connection_aspiration"},
        ]
        dist = build_distributions(signals)
        assert dist["pillar"]["Education & Knowledge"] == 2
        assert dist["beneficiary"]["self"] == 1
        assert dist["beneficiary"]["family"] == 1


class TestAlignmentScore:
    def test_aligned_signal(self):
        # A signal matching the most common category should score higher
        signals = make_diverse_signals(100)
        signal = {
            "primary_pillar": "Education & Knowledge",
            "beneficiary": "self",
            "emotional_valence": "hope",
            "signal_type": "self_directed_aspiration",
            "quality": "valid",
        }
        score = alignment_score(signal, signals)
        assert 0.0 <= score <= 1.0

    def test_empty_reference(self):
        signal = SAMPLE_VALID_SIGNAL
        assert alignment_score(signal, []) == 0.0


class TestComputeDivergences:
    def test_identical_zero(self):
        dist = {"pillar": {"a": 10}, "beneficiary": {"x": 5},
                "emotional_valence": {"hope": 8}, "signal_type": {"self_directed_aspiration": 3}}
        divs = compute_divergences(dist, dist)
        for dim in divs:
            assert divs[dim] < 1e-10


class TestAspirationAlignmentScore:
    def test_perfect_alignment(self):
        divs = {"pillar": 0.0, "beneficiary": 0.0, "emotional_valence": 0.0, "signal_type": 0.0}
        assert aspiration_alignment_score(divs) == 1.0

    def test_max_divergence(self):
        divs = {"pillar": 1.0, "beneficiary": 1.0, "emotional_valence": 1.0, "signal_type": 1.0}
        assert aspiration_alignment_score(divs) == 0.0


class TestBootstrapCI:
    def test_basic_ci(self):
        values = [1.0] * 50 + [0.0] * 50
        point, lo, hi = bootstrap_ci(values)
        assert 0.4 <= point <= 0.6
        assert lo < point
        assert hi > point

    def test_constant_values(self):
        values = [5.0] * 100
        point, lo, hi = bootstrap_ci(values)
        assert point == 5.0
        assert lo == 5.0
        assert hi == 5.0

    def test_empty_values(self):
        point, lo, hi = bootstrap_ci([])
        assert point == 0.0
        assert lo == 0.0
        assert hi == 0.0

    def test_single_value(self):
        point, lo, hi = bootstrap_ci([3.14])
        assert point == 3.14
