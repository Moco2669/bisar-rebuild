"""Show a BISAR input file, and the responses once the solver can produce them."""

import sys
from pathlib import Path

from bisar.engine import solve
from bisar.inp import read_input

_SAMPLE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "nrb1.inp"


def _shown(value: float, scale: float) -> float:
    if abs(value) <= 1e-4 * max(abs(scale), 1e-30):
        return 0.0
    return value


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
        total_displacement = result.total_displacement
        total_stress = result.total_stress
        if total_displacement is None or total_stress is None:
            continue
        ux, uy, uz = (
            _shown(total_displacement.x, total_displacement.z),
            _shown(total_displacement.y, total_displacement.z),
            total_displacement.z,
        )
        xx, yy, zz = (
            _shown(total_stress.xx, total_stress.zz),
            _shown(total_stress.yy, total_stress.zz),
            total_stress.zz,
        )
        print(
            f"  position {result.position}: ux={ux:.4E}"
            f"  uy={uy:.4E}"
            f"  uz={uz:.4E}"
            f"  xx={xx:.4E}"
            f"  yy={yy:.4E}"
            f"  zz={zz:.4E}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
