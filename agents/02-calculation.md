# Agent 2 — Calculation

You implement `bisar.engine.solve` so the oracle tests pass. You do not build the window.

## Read first

- `AGENTS.md`
- `src/bisar/model.py` and `src/bisar/engine.py`
- The xfail tests in `tests/test_engine_oracle.py` and any newer oracle tests
- A layered-elastic reference for a stack of infinite horizontal layers on a half-space: modulus, Poisson's ratio, thickness, uniform circular vertical stress, optional horizontal traction, and a shear spring between layers

## Method

Represent each load in cylindrical coordinates, integrate the Hankel transforms through the layers, and superpose loads. At an interface the shear spring relates the horizontal displacement jump to the shear stress. Map the local radial and tangential components onto the fixed X, Y, Z axes used in the report.

Start with the fully bonded, vertical-load centerline in `tests/fixtures/nrb1_expected.json`. Remove `xfail` only from tests that now pass. Leave the others strict.

Relative tolerance against the printed values is `1e-3`, because the original report keeps four figures.

## When a number will not match

Only then open `D:\BISAR3\BISAR_4W.DLL` or `D:\BISAR3\bisar\BISAR.EXE` and find the one routine responsible for that quantity. Write down the numerical choice in `docs/numerical-notes.md` in your own words, with the file offset you read. Do not paste disassembly dumps into the repo. Do not change the Fortran files.

## Done

The centerline test is a normal passing test. `pytest` passes. The public functions still return `PointResult` values.
