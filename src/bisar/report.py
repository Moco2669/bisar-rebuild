"""Present solver results in the same four-digit scientific layout as BISAR."""

from __future__ import annotations

import math


def fortran_e(value: float) -> str:
    """BISAR's printed form, for example .5808E-04 or -.3883E+05."""
    if value == 0.0 or not math.isfinite(value):
        return ".0000E+00"
    sign = "-" if value < 0.0 else ""
    magnitude = abs(value)
    exponent = math.floor(math.log10(magnitude)) + 1
    mantissa = magnitude / 10.0**exponent
    digits = int(round(mantissa * 10000))
    if digits == 10000:
        digits = 1000
        exponent += 1
    if digits == 0:
        return ".0000E+00"
    return f"{sign}.{digits:04d}E{exponent:+03d}"


def result_rows(results: list[dict]) -> list[dict]:
    rows = []
    for index, result in enumerate(results, start=1):
        point = result["point"]
        first = result["per_load"][0]
        cyl = first["cylindrical"]
        rows.append(
            {
                "position": index,
                "layer": point.layer + 1,
                "x": point.x,
                "y": point.y,
                "z": point.z,
                "distance": first["r"],
                "theta_deg": math.degrees(first["theta"]),
                "cylindrical": {key: fortran_e(cyl[key]) for key in ("ur", "uz", "sr", "st", "sz", "trz", "er", "et", "ez", "erz")},
                "cartesian": {
                    key: fortran_e(result[key])
                    for key in ("ux", "uy", "uz", "sx", "sy", "sz", "txy", "txz", "tyz", "ex", "ey", "ez", "exy", "exz", "eyz")
                },
                "principals": [
                    {
                        "stress": fortran_e(item["stress"]),
                        "strain": fortran_e(item["strain"]),
                        "direction": [round(float(component), 4) for component in item["direction"]],
                    }
                    for item in result["principals"]
                ],
                "shears": [
                    {
                        "stress": fortran_e(item["stress"]),
                        "strain": fortran_e(item["strain"]),
                        "midpoint": fortran_e(item["midpoint"]),
                        "direction": [round(float(component), 4) for component in item["direction"]],
                    }
                    for item in result["shears"]
                ],
                "strain_energy": fortran_e(result["strain_energy"]),
                "distortion_energy": fortran_e(result["distortion_energy"]),
                "raw": {
                    "uz": result["uz"],
                    "sx": result["sx"],
                    "sy": result["sy"],
                    "sz": result["sz"],
                },
            }
        )
    return rows
