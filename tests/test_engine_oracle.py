"""The solver must reproduce the recorded BISAR-PC centerline responses."""

import json
from pathlib import Path

import pytest

from bisar.engine import solve
from bisar.inp import parse_input

FIXTURES = Path(__file__).parent / "fixtures"
PROBLEM = parse_input((FIXTURES / "nrb1.inp").read_text(encoding="ascii"))
EXPECTED = json.loads((FIXTURES / "nrb1_expected.json").read_text(encoding="ascii"))


def test_nrb1_matches_recorded_centerline():
    results = solve(PROBLEM)
    assert len(results) == len(EXPECTED["points"])
    for result, expected in zip(results, EXPECTED["points"]):
        assert result.position == expected["position"]
        assert result.layer == expected["layer"]
        assert result.z == pytest.approx(expected["z"])
        assert result.displacement.vertical == pytest.approx(expected["uz"], rel=1e-3)
        assert result.stress.vertical == pytest.approx(expected["sz"], rel=1e-3)
        assert result.stress.radial == pytest.approx(expected["sr"], rel=1e-3)
        assert result.strain.vertical == pytest.approx(expected["ez"], rel=1e-3)
        assert result.strain.radial == pytest.approx(expected["er"], rel=1e-3)
