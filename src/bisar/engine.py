"""Layered-elastic solver.

The calculation agent fills this in. Tests already name the quantities it must
return for the recorded four-layer case.
"""

from bisar.model import PointResult, Problem


def solve(problem: Problem) -> tuple[PointResult, ...]:
    raise NotImplementedError(
        "The layered-elastic solver is not implemented yet. "
        "See agents/02-calculation.md."
    )
