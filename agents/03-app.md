# Agent 3 — Application

You build the program a person uses. You call `bisar.engine.solve`. You do not change the solver to hide a wrong number.

## Read first

- `AGENTS.md`
- `docs/behavior.md`, once Agent 1 has started it
- `D:\BISAR3\BISAR3.PDF` for the order of work: describe the structure, place the loads, choose positions, calculate, then read a block report and a detailed report. Treat the manual as a checklist. Do not copy its wording, tables, or figures into the repo.

## Build

Use the Python standard library first. A single-page interface is enough until the centerline oracle passes:

- edit layers, loads, and positions
- run the solver
- show vertical displacement and the three normal stresses at each position

After that, follow the manual's remaining workflow one screen at a time: saving a project, the standard dual wheel, shear, slip, and the two reports. Each screen gets a test that drives the function behind it. Do not reproduce the old Visual Basic grid, gauge, or database widgets.

## Done

The new screen is covered by a test, `pytest` passes, and every number on the screen comes from `solve`.
