from pathlib import Path

from bisar.inp import parse_input

FIXTURE = Path(__file__).parent / "fixtures" / "nrb1.inp"


def test_nrb1_layers_loads_and_positions():
    problem = parse_input(FIXTURE.read_text(encoding="ascii"))

    assert problem.name == "NRB-1"
    assert len(problem.layers) == 4
    assert problem.layers[0].modulus == 3.5e10
    assert problem.layers[0].thickness == 0.05
    assert problem.layers[-1].thickness == 0.0
    assert problem.layers[1].shear_spring == 0.0

    assert len(problem.loads) == 1
    load = problem.loads[0]
    assert load.stress == 7.0e5
    assert load.radius == 9.53654e-2
    assert load.shear_stress == 0.0

    assert [point.layer for point in problem.points] == [1, 1, 1, 2, 3, 4]
    assert [point.number for point in problem.points] == [1, 2, 3, 4, 5, 6]
    assert problem.points[0].z == 0.0
    assert problem.points[1].z == 1.0e-3
    assert problem.points[3].z == 0.125
