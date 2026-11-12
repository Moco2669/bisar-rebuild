"""The calculation window shows displacements and stresses taken from the solver."""

import tkinter as tk
from pathlib import Path

from bisar.engine import solve
from bisar.inp import parse_input
from bisar.screen import (
    CalculationWindow,
    apply_standard_positions,
    calculate_draft,
    choose_layer,
    display_compliance,
    draft_from_problem,
    resize_draft,
    sample_draft,
    shown,
    store_compliance,
)

FIXTURE = Path(__file__).parent / "fixtures" / "nrb1.inp"
DUAL = Path(__file__).parent / "fixtures" / "dual.inp"


def test_the_starting_structure_shows_the_solver_results_for_the_centerline():
    results, error = calculate_draft(sample_draft())
    assert error is None and results is not None
    problem = parse_input(FIXTURE.read_text(encoding="ascii"))
    for result, expected in zip(results, solve(problem)):
        displacement = result.total_displacement
        stress = result.total_stress
        expected_displacement = expected.total_displacement
        expected_stress = expected.total_stress
        assert displacement is not None and stress is not None
        assert expected_displacement is not None and expected_stress is not None
        assert shown(displacement.z, displacement.z) == shown(expected_displacement.z, expected_displacement.z)
        assert shown(stress.xx, stress.zz) == shown(expected_stress.xx, expected_stress.zz)
        assert shown(stress.yy, stress.zz) == shown(expected_stress.yy, expected_stress.zz)
        assert shown(stress.zz, stress.zz) == shown(expected_stress.zz, expected_stress.zz)


def test_changing_a_modulus_changes_the_displayed_settlement():
    draft = sample_draft()
    original, error = calculate_draft(draft)
    assert error is None and original is not None
    draft.layers[0]["modulus"] = "1e9"
    edited, error = calculate_draft(draft)
    assert error is None and edited is not None
    original_uz = original[0].total_displacement
    edited_uz = edited[0].total_displacement
    assert original_uz is not None and edited_uz is not None
    assert shown(original_uz.z, original_uz.z) != shown(edited_uz.z, edited_uz.z)


def test_a_bad_entry_is_reported_without_results():
    draft = sample_draft()
    draft.layers[0]["poisson"] = "abc"
    results, error = calculate_draft(draft)
    assert results is None
    assert error == "Layer 1 Poisson's ratio must be a number."


def test_position_count_adds_a_row_without_calculating():
    draft = resize_draft(sample_draft(), positions=7)
    assert len(draft.points) == 7
    assert draft.points[-1]["z"] == ""
    assert len(draft.layers) == 4


def test_an_interface_can_be_kept_on_one_side_or_both():
    above = sample_draft()
    above.points[0]["z"] = "0.05"
    above.points[0]["layer"] = "1/2"
    choose_layer(above, 0, "above")
    assert above.points[0]["layer"] == "1"
    both = sample_draft()
    both.points[0]["z"] = "0.05"
    both.points[0]["layer"] = "1/2"
    choose_layer(both, 0, "both")
    assert [point["layer"] for point in both.points[:2]] == ["1", "2"]
    assert both.points[0]["z"] == both.points[1]["z"] == "0.05"


def test_standard_dual_positions_match_the_recorded_case():
    problem = parse_input(DUAL.read_text(encoding="ascii"))
    draft = draft_from_problem(problem)
    apply_standard_positions(draft)
    assert len(draft.points) == len(problem.points)
    for point, expected in zip(draft.points, problem.points):
        assert int(point["layer"]) == expected.layer
        assert float(point["x"]) == expected.x
        assert float(point["y"]) == expected.y
        assert float(point["z"]) == expected.z


def test_standard_compliance_is_the_reduced_value_scaled_by_the_layer():
    modulus = "2e9"
    poisson = "0.5"
    assert store_compliance("1.125E-08", "standard", modulus, poisson) == "15"
    assert display_compliance("15", "standard", modulus, poisson) == "1.13E-08"


def test_the_window_uses_counts_and_shows_the_solver_settlement():
    root = tk.Tk()
    root.withdraw()
    window = CalculationWindow(root)
    try:
        texts = window.widget_texts()
        assert "No of Layers (1-10):" in texts
        assert "No of Position Entries (1-10):" in texts
        assert "No of Circular Loads (1-10):" in texts
        assert "Add layer" not in texts
        assert "Add position" not in texts
        assert window.layer_count.get() == "4"
        assert window.position_count.get() == "6"
        window.calculate()
        displacement = solve(parse_input(FIXTURE.read_text(encoding="ascii")))[0].total_displacement
        assert displacement is not None
        assert shown(displacement.z, displacement.z) in window.result_values
        assert window.results_window is not None
        window.results_window.withdraw()
    finally:
        root.destroy()
