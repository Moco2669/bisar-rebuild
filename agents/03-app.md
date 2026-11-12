# Agent 3 — Application

You build the program a person uses. You call `bisar.engine.solve`. You do not change the solver to hide a wrong number.

## Read first

- `AGENTS.md` and the current milestone in `docs/ROADMAP.md`
- `docs/behavior.md`
- `D:\BISAR3\BISAR3.PDF` for the order of work: describe the structure, place the loads, choose positions, calculate, then read a block report and a detailed report. Treat the manual as a checklist. Do not copy its wording, tables, or figures into the repo.

The solver already matches the centerline, the standard dual wheel, interface slip, and the horizontal shear load. The calculation window in `src/bisar/screen.py` is a desktop window. It edits that structure and shows the displacements and stresses from `solve`. Later screens show only values `solve` already gets right.

## Build

Use the Python standard library first. The program a person opens is a desktop window, not a page in a browser. The current screen is the one named in the roadmap.

Match the input panel in the manual as closely as the current milestone allows. Loads, layers, and positions are tabs in one system window. Each tab has a count for its rows (the layer count and the position count, and the load count the same way). Full friction, the spring-compliance choice, the three load modes, and the layer choice at an interface belong on that panel. Keep those counts. Do not replace them with add and remove buttons, and do not move the calculation back into a browser page. Do not copy the manual's wording, tables, or figures into the repo.

The remaining workflow is one screen at a time: saving a project and the two reports. Each screen gets a test that drives the function behind it. A control the milestone does not implement yet should say so, rather than pretend to save or calculate.

## Done

The new screen is covered by a test, `pytest` passes, and every number on the screen comes from `solve`.
