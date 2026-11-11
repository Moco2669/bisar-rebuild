"""Show a BISAR input file, and the responses once the solver can produce them."""

import sys
from pathlib import Path

from bisar.engine import solve
from bisar.inp import read_input

_SAMPLE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "nrb1.inp"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    path = Path(args[0]) if args else _SAMPLE
    if not path.is_file():
        print(f"Input file not found: {path}", file=sys.stderr)
        return 1
    problem = read_input(path)
    print(problem.name)
    print(f"{len(problem.layers)} layers, {len(problem.loads)} loads, {len(problem.points)} positions")
    for index, layer in enumerate(problem.layers, start=1):
        print(
            f"  layer {index}: E={layer.modulus:.6E}  nu={layer.poisson:.2f}"
            f"  h={layer.thickness:.6E}"
        )
    try:
        results = solve(problem)
    except NotImplementedError as exc:
        print(exc)
        return 0
    for result in results:
        print(
            f"  position {result.position}: uz={result.displacement.vertical:.4E}"
            f"  sr={result.stress.radial:.4E}"
            f"  st={result.stress.tangential:.4E}"
            f"  sz={result.stress.vertical:.4E}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
