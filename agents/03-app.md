# Agent 3 — Application

You build the program a person uses. You call `bisar.engine.solve`. You do not change the solver to hide a wrong number.

## Read first

- `AGENTS.md` and the current milestone in `docs/ROADMAP.md`
- `docs/behavior.md`
- `D:\BISAR3\BISAR3.PDF` for the order of work: describe the structure, place the loads, choose positions, calculate, then read a block report and a detailed report. Treat the manual as a checklist. Do not copy its wording, tables, or figures into the repo.

The solver already matches the centerline, the standard dual wheel, interface slip, and the horizontal shear load. The screen shows only values `solve` already gets right.

## Build

Use the Python standard library first. The current screen is the one named in the roadmap. The first page edits layers, loads, and positions, runs the solver, and shows the displacements and stresses at each position.

Later milestones follow the manual's remaining workflow one screen at a time: saving a project and the two reports. Each screen gets a test that drives the function behind it. Do not reproduce the old Visual Basic grid, gauge, or database widgets.

## Done

The new screen is covered by a test, `pytest` passes, and every number on the screen comes from `solve`.
