from pathlib import Path

import pytest

from bisar.report import parse_report

FIXTURE = Path(__file__).parent / "fixtures" / "one_position.txt"
RECORDED = Path(r"D:\BISAR3\DUMMY.OUT")


def test_one_position_block():
    result = parse_report(FIXTURE.read_text(encoding="ascii"))[0]
    assert result.position == 1
    assert result.layer == 1
    assert result.z == 0.0
    assert result.displacement.vertical == pytest.approx(1.399e-4)
    assert result.stress.vertical == pytest.approx(-7.0e5)
    assert result.stress.radial == pytest.approx(-3.034e6)
    assert result.strain.vertical == pytest.approx(4.069e-5)


@pytest.mark.skipif(not RECORDED.exists(), reason="recorded BISAR report is not on this machine")
def test_recorded_report_has_six_centerline_points():
    results = parse_report(RECORDED.read_text(encoding="latin-1"))
    assert [item.position for item in results] == [1, 2, 3, 4, 5, 6]
    assert results[0].stress.vertical == pytest.approx(-7.0e5, rel=1e-4)
    assert results[5].displacement.vertical == pytest.approx(1.057e-4, rel=1e-3)
