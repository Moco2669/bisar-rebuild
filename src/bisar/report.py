"""Reader for the quantities in a BISAR-PC detailed report.

Only the position blocks are kept: coordinates and the radial, tangential, and
vertical displacement, stress, and strain. The prose of the report is not stored.
"""

import re
from pathlib import Path

from bisar.model import Components, PointResult

_BLOCK = re.compile(r"POSITION NUMBER:\s*(\d+)", re.IGNORECASE)
_LAYER = re.compile(r"LAYER NUMBER\s*:\s*(\d+)", re.IGNORECASE)
_NUMBER = r"[+-]?(?:\d+\.\d+|\.\d+)E[+-]\d{2}"
_COORDS = re.compile(
    rf"({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})",
    re.IGNORECASE,
)
_TRIPLE = re.compile(
    rf"Radial\s*:\s*({_NUMBER})\s+Tangential:\s*({_NUMBER})\s+Vertical\s*:\s*({_NUMBER})",
    re.IGNORECASE,
)


def _components(match: re.Match[str]) -> Components:
    return Components(
        radial=float(match.group(1)),
        tangential=float(match.group(2)),
        vertical=float(match.group(3)),
    )


def _section(block: str, heading: str) -> str:
    start = block.upper().find(heading.upper())
    if start < 0:
        raise ValueError(f"report block has no {heading} section")
    rest = block[start + len(heading) :]
    for later in ("STRESSES", "STRAINS", "T O T A L"):
        if later == heading.upper():
            continue
        stop = rest.upper().find(later)
        if stop >= 0:
            return rest[:stop]
    return rest


def parse_report(text: str) -> tuple[PointResult, ...]:
    """Return one result per ``POSITION NUMBER`` block."""
    parts = _BLOCK.split(text)
    # split keeps the captured position numbers: [preamble, num, body, num, body, ...]
    if len(parts) < 3:
        raise ValueError("report contains no positions")
    results: list[PointResult] = []
    for number_text, body in zip(parts[1::2], parts[2::2]):
        layer_match = _LAYER.search(body)
        coord_match = _COORDS.search(body)
        if layer_match is None or coord_match is None:
            raise ValueError(f"position {number_text} is missing its layer or coordinates")
        displacement = _components(_require_triple(_section(body, "DISPLACEMENTS")))
        stress = _components(_require_triple(_section(body, "STRESSES")))
        strain = _components(_require_triple(_section(body, "STRAINS")))
        results.append(
            PointResult(
                position=int(number_text),
                layer=int(layer_match.group(1)),
                x=float(coord_match.group(1)),
                y=float(coord_match.group(2)),
                z=float(coord_match.group(3)),
                displacement=displacement,
                stress=stress,
                strain=strain,
            )
        )
    return tuple(results)


def _require_triple(section: str) -> re.Match[str]:
    match = _TRIPLE.search(section)
    if match is None:
        raise ValueError(f"could not read a radial/tangential/vertical line in {section!r}")
    return match


def read_report(path: Path) -> tuple[PointResult, ...]:
    return parse_report(path.read_text(encoding="latin-1"))
