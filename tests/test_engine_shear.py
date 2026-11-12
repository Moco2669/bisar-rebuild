"""A circular load with a horizontal shear force on a fully bonded structure."""

import json
from pathlib import Path

import pytest

from bisar.engine import solve
from bisar.inp import parse_input

FIXTURES = Path(__file__).parent / "fixtures"
PROBLEM = parse_input((FIXTURES / "shear.inp").read_text(encoding="ascii"))
EXPECTED = json.loads((FIXTURES / "shear_expected.json").read_text(encoding="ascii"))


def test_shear_input_has_a_horizontal_load_and_full_friction():
    assert PROBLEM.loads[0].shear_stress == pytest.approx(1.444e5)
    assert PROBLEM.loads[0].shear_direction == 0.0
    assert all(layer.shear_spring == 0.0 for layer in PROBLEM.layers)
    assert [point.layer for point in PROBLEM.points] == [1, 2, 1, 2, 1, 2, 3]


def test_shear_matches_recorded_totals():
    results = solve(PROBLEM)
    for result, expected in zip(results, EXPECTED["points"], strict=True):
        displacement = result.total_displacement
        stress = result.total_stress
        strain = result.total_strain
        assert displacement is not None and stress is not None and strain is not None
        assert displacement.x == pytest.approx(expected["ux"], rel=1e-3, abs=1e-9)
        assert displacement.y == pytest.approx(expected["uy"], rel=1e-3, abs=1e-9)
        assert displacement.z == pytest.approx(expected["uz"], rel=1e-3, abs=1e-9)
        assert stress.xx == pytest.approx(expected["xx"], rel=1e-3, abs=1e-2)
        assert stress.yy == pytest.approx(expected["yy"], rel=1e-3, abs=1e-2)
        assert stress.zz == pytest.approx(expected["zz"], rel=1e-3, abs=1e-2)
        assert stress.yz == pytest.approx(expected["yz"], rel=1e-3, abs=1e-2)
        assert stress.xz == pytest.approx(expected["xz"], rel=1e-3, abs=1e-2)
        # XY is the small remainder of two opposing slopes, so half a pascal is the match.
        assert stress.xy == pytest.approx(expected["xy"], rel=1e-3, abs=0.5)
        assert strain.xx == pytest.approx(expected["exx"], rel=1e-3, abs=1e-9)
        assert strain.yy == pytest.approx(expected["eyy"], rel=1e-3, abs=1e-9)
        assert strain.zz == pytest.approx(expected["ezz"], rel=1e-3, abs=1e-9)
