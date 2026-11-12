# Orchestrator

This repository rebuilds the BISAR pavement calculation as a Python program and checks it against BISAR-PC. The orchestrator does not implement a feature itself. It assigns one of the three agents below, reviews the diff, and runs `pytest`.

The current milestone is in `docs/ROADMAP.md`. Finish that one before opening the next. Signs, coefficients, and quadrature choices that the tests already rely on are in `docs/solver-notes.md`. Read that before changing the solver.

Work inside a milestone proceeds in this order:

1. `agents/01-tests-and-docs.md` — a failing or extended test that names the next behavior.
2. `agents/02-calculation.md` — the solver change that makes that test pass.
3. `agents/03-app.md` — a screen or report, and only for behavior the solver already gets right.

The Fortran library is not a fourth project. Agent 02 reads it only after a test shows a number the published layer method does not explain.

## Local originals

These stay on the machine. They are not copied into git.

- Manual: `D:\BISAR3\BISAR3.PDF` (Shell, confidential). Use it as a behavior checklist. Do not paste its prose, figures, or page scans into this repository.
- Recorded case: `D:\BISAR3\DUMMY.INP` and `D:\BISAR3\DUMMY.OUT`.
- Original program: `D:\BISAR3\bisar\BISAR.EXE`, run under otvdm when a new oracle case is needed.

## Done means

- `python -m pytest` passes.
- A solver test that is expected to fail is marked `xfail(strict=True)` and names the missing behavior.
- No file from `D:\BISAR3` and no text copied from the manual is added to the commit.
