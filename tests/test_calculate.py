"""The Calculate path against the Boussinesq closed form and a BISAR 3 report."""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bisar.model import layers_from_screen, loads_from_screen, positions_from_screen
from bisar.report import fortran_e
from bisar.solver import Layer, Load, Point, analyse, response_one_load


def _rel(actual, expected):
    scale = max(abs(expected), 1e-30)
    return abs(actual - expected) / scale


class HalfSpaceTest(unittest.TestCase):
    def test_centerline_matches_boussinesq(self):
        young, poisson, pressure, radius, depth = 5e9, 0.35, 5.774e5, 0.105, 0.3
        slant = math.sqrt(radius * radius + depth * depth)
        vertical = -pressure * (1.0 - depth**3 / slant**3)
        radial = -(
            (pressure / 2.0) * (1.0 + 2.0 * poisson)
            - pressure * (1.0 + poisson) * depth / slant
            + (pressure / 2.0) * depth**3 / slant**3
        )
        settlement = (1.0 + poisson) * pressure / young * (
            radius * radius / slant + (1.0 - 2.0 * poisson) * (slant - depth)
        )
        got = response_one_load(
            [Layer(young, poisson, None)],
            Load(pressure, radius),
            0.0,
            depth,
            0,
        )
        self.assertLess(_rel(got["sz"], vertical), 1e-8)
        self.assertLess(_rel(got["sr"], radial), 1e-8)
        self.assertLess(_rel(got["uz"], settlement), 1e-8)


class BisarReportTest(unittest.TestCase):
    """Numbers printed by BISAR-PC 2.0 for DUMMY.OUT, four significant figures."""

    def setUp(self):
        self.layers = layers_from_screen(
            [
                {"modulus_mpa": 5000, "poisson": 0.35, "thickness_m": 0.30, "alk_m": 10.5},
                {"modulus_mpa": 1000, "poisson": 0.35, "thickness_m": 0.20, "alk_m": 0},
                {"modulus_mpa": 800, "poisson": 0.35, "thickness_m": 0.15, "alk_m": 0},
                {"modulus_mpa": 200, "poisson": 0.35, "halfspace": True},
            ]
        )
        self.loads = loads_from_screen(
            [{"mode": "stress-radius", "stress_mpa": 0.577433, "radius_m": 0.105}]
        )

    def test_slip_case_matches_printed_report(self):
        # Cylindrical values from DUMMY.OUT. The last printed digit is the tolerance.
        expected = [
            dict(layer=1, uz=0.5808e-4, sr=0.2076e6, st=0.2076e6, sz=-0.3883e5, ur=0.0, tr=0.0),
            dict(layer=2, uz=0.5808e-4, sr=-0.3743e5, st=-0.3743e5, sz=-0.3883e5, ur=0.0, tr=0.0),
            dict(layer=1, uz=0.5320e-4, sr=0.8731e5, st=0.1310e6, sz=-0.2128e5, ur=0.4315e-5, tr=-0.2130e4, x=0.2),
            dict(layer=2, uz=0.5320e-4, sr=-0.2100e5, st=-0.2342e5, sz=-0.2128e5, ur=-0.1724e-5, tr=-0.2130e4, x=0.2),
            dict(layer=3, uz=0.5024e-4, sr=0.1519e5, st=0.1519e5, sz=-0.1047e5, ur=0.0, tr=0.0, z=0.65),
        ]
        points = []
        for row in expected:
            points.append(Point(row.get("x", 0.0), 0.0, row.get("z", 0.30), row["layer"] - 1))
        results = analyse(self.layers, self.loads, points)
        for row, result in zip(expected, results):
            cyl = result["per_load"][0]["cylindrical"]
            for key in ("uz", "sr", "st", "sz", "ur", "trz"):
                want = row["tr" if key == "trz" else key]
                got = cyl[key]
                self.assertLess(
                    _rel(got, want) if want else abs(got),
                    1.5e-3,
                    f"{key} got {got} want {want}",
                )
            printed = fortran_e(cyl["uz"])
            reference = fortran_e(row["uz"])
            self.assertLessEqual(_digit_gap(printed, reference), 1, f"{printed} vs {reference}")

    def test_interface_auto_returns_both_sides(self):
        points = positions_from_screen(
            [{"x_m": 0, "y_m": 0, "z_m": 0.30, "layer": "auto"}],
            self.layers,
        )
        self.assertEqual([point.layer for point in points], [0, 1])


def _digit_gap(left: str, right: str) -> int:
    """How many units the last displayed digit differs by, after aligning exponents."""
    if left == right:
        return 0
    def parts(text):
        sign = -1 if text.strip().startswith("-") else 1
        mantissa, exponent = text.strip().lstrip("-").split("E")
        return sign * int(mantissa[1:]), int(exponent)
    lv, le = parts(left)
    rv, re = parts(right)
    if le != re:
        return 99
    return abs(lv - rv)


if __name__ == "__main__":
    unittest.main()
