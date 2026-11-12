# Agent 2 — Calculation

You implement `bisar.engine.solve` so the oracle tests pass. You do not build the window.

## Read first

- `AGENTS.md` and the current milestone in `docs/ROADMAP.md`
- `docs/solver-notes.md` before changing a sign, a coefficient, or the quadrature
- `src/bisar/model.py` and `src/bisar/engine.py`
- The xfail tests, if the milestone has any, and the passing oracle tests

The bonded centerline, the standard dual wheel, interface slip, and the horizontal shear load already pass. Leave those formulas as `docs/solver-notes.md` records them.

## Method

Represent each load in cylindrical coordinates, integrate the Hankel transforms through the layers, and superpose loads. At an interface the shear spring relates the horizontal displacement jump to the shear stress. A horizontal traction is the separate Galerkin field, added to the vertical solution. Map the local components onto the fixed X, Y, Z axes used in the report.

Remove `xfail` only from tests that now pass. Leave the others strict.

Relative tolerance against the printed values is `1e-3`, because the original report keeps four figures.

## When a number will not match

Only then open `D:\BISAR3\BISAR_4W.DLL` or `D:\BISAR3\bisar\BISAR.EXE` and find the one routine responsible for that quantity. Write the numerical choice in `docs/solver-notes.md` in your own words, with the file offset you read. Do not paste disassembly dumps into the repo. Do not change the Fortran files.

## Done

The milestone's solver tests pass with no remaining `xfail`. `pytest` passes. The public functions still return `PointResult` values.
