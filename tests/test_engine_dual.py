"""Two vertical wheels, including points that are not on a load axis."""

import json
from pathlib import Path

import pytest

from bisar.engine import solve
from bisar.inp import parse_input

FIXTURES = Path(__file__).parent / "fixtures"
PROBLEM = parse_input((FIXTURES / "dual.inp").read_text(encoding="ascii"))
EXPECTED = json.loads((FIXTURES / "dual_expected.json").read_text(encoding="ascii"))


def test_dual_input_has_two_wheels_and_eight_positions():
    assert PROBLEM.name == "dual wheel"
    assert len(PROBLEM.loads) == 2
    assert PROBLEM.loads[0].y == pytest.approx(-0.1575)
    assert PROBLEM.loads[1].y == pytest.approx(0.1575)
    assert [point.layer for point in PROBLEM.points] == [1, 1, 2, 2, 3, 3, 4, 4]
    assert PROBLEM.points[1].y == pytest.approx(-0.1575)


def test_dual_wheel_matches_recorded_totals():
    results = solve(PROBLEM)
    assert len(results) == len(EXPECTED["points"])
    for result, expected in zip(results, EXPECTED["points"]):
        assert result.position == expected["position"]
        assert result.layer == expected["layer"]
        total_displacement = result.total_displacement
        total_stress = result.total_stress
        total_strain = result.total_strain
        assert total_displacement is not None and total_stress is not None and total_strain is not None
        assert total_displacement.x == pytest.approx(expected["ux"], rel=1e-3, abs=1e-9)
        assert total_displacement.y == pytest.approx(expected["uy"], rel=1e-3, abs=1e-9)
        assert total_displacement.z == pytest.approx(expected["uz"], rel=1e-3, abs=1e-9)
        assert total_stress.xx == pytest.approx(expected["xx"], rel=1e-3, abs=1e-2)
        assert total_stress.yy == pytest.approx(expected["yy"], rel=1e-3, abs=1e-2)
        assert total_stress.zz == pytest.approx(expected["zz"], rel=1e-3, abs=1e-2)
        assert total_stress.yz == pytest.approx(expected["yz"], rel=1e-3, abs=1e-2)
        assert total_strain.xx == pytest.approx(expected["exx"], rel=1e-3, abs=1e-9)
        assert total_strain.yy == pytest.approx(expected["eyy"], rel=1e-3, abs=1e-9)
        assert total_strain.zz == pytest.approx(expected["ezz"], rel=1e-3, abs=1e-9)
        assert total_strain.yz == pytest.approx(expected["eyz"], rel=1e-3, abs=1e-9)
