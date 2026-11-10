"""Reader for the BISAR-PC calculation input file.

Numbers are Fortran-style (``3.50000E+10``). A fixed-width record sometimes
glues two of them together, as in ``7.00000E+059.53654E-02``, so values are
taken with a number scanner rather than by splitting on spaces.
"""

import re
from pathlib import Path

from bisar.model import Layer, Load, Problem, QueryPoint

# Exponents in these records are two digits. A third digit belongs to the next
# number when the file glues them together: "7.00000E+059.53654E-02".
_NUMBER = re.compile(r"[+-]?(?:\d+\.\d+|\.\d+)E[+-]\d{2}", re.IGNORECASE)
_LOAD_CODE = re.compile(r"^(STRS|LOAD|RAD)\b", re.IGNORECASE)


def _numbers(line: str) -> list[float]:
    return [float(token) for token in _NUMBER.findall(line)]


def parse_input(text: str) -> Problem:
    """Parse one BISAR-PC system from an input file."""
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("input file is empty")
    name = lines[0].strip()
    layers: list[Layer] = []
    loads: list[Load] = []
    points: list[QueryPoint] = []
    seen_loads = False
    for line in lines[1:]:
        values = _numbers(line)
        head = line.lstrip()[:4].upper()
        if _LOAD_CODE.match(head):
            seen_loads = True
            if len(values) < 6:
                raise ValueError(f"load record has {len(values)} numbers: {line!r}")
            loads.append(
                Load(
                    stress=values[0],
                    radius=values[1],
                    x=values[2],
                    y=values[3],
                    shear_stress=values[4],
                    shear_direction=values[5],
                )
            )
            continue
        if not seen_loads and len(values) == 4 and "E" in line.upper():
            layers.append(
                Layer(
                    modulus=values[0],
                    poisson=values[1],
                    thickness=values[2],
                    shear_spring=values[3],
                )
            )
            continue
        if seen_loads:
            # A position record starts with the layer number in two columns,
            # then X, Y, Z. The layer number is glued to X: "010.00000E+00".
            head = line.lstrip()
            if len(head) < 2 or not head[:2].isdigit():
                continue
            values = _numbers(head[2:])
            if len(values) < 3:
                continue
            points.append(
                QueryPoint(
                    number=len(points) + 1,
                    layer=int(head[:2]),
                    x=values[0],
                    y=values[1],
                    z=values[2],
                    axis_angle=values[3] if len(values) > 3 else 0.0,
                )
            )
    if not layers or not loads or not points:
        raise ValueError("input is missing layers, loads, or positions")
    return Problem(name=name, layers=tuple(layers), loads=tuple(loads), points=tuple(points))


def read_input(path: Path) -> Problem:
    return parse_input(path.read_text(encoding="latin-1"))
