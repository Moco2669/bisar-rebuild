# Roadmap

One milestone at a time. A milestone is finished when its tests pass and `run.bat` shows the behavior named below. The next milestone does not start early.

The manual in `D:\BISAR3\BISAR3.PDF` is the checklist for what a person can do. It is not copied into this repository.

## Done

**M0 — Harness.** The sample input and the detailed report can be read. The four-layer centerline from one recorded run is stored as numbers. `run.bat` prints that structure.

**M1 — Bonded centerline.** `solve` reproduces `tests/fixtures/nrb1_expected.json`: one vertical circular load, four fully bonded layers, six positions on the load axis. `run.bat` prints vertical displacement and the normal stresses for that file. The centerline test passes.

**M2 — Several loads.** `solve` reproduces `tests/fixtures/dual_expected.json`: the standard dual wheel, eight positions, including points off a load axis. The combined response is the Cartesian total. `run.bat tests\fixtures\dual.inp` prints it.

**M3 — Shear and slip.** `solve` reproduces `tests/fixtures/slip_expected.json` (reduced compliance 10.5 m under the top layer) and `tests/fixtures/shear_expected.json` (a 5 kN horizontal load along X on the bonded structure). `run.bat tests\fixtures\shear.inp` prints the Cartesian total, including the shear stresses.

## Next

**M4 — A calculation screen.** One page where a person edits layers, loads, and positions, runs the calculation, and reads the displacements and normal stresses. The page is covered by a test and only displays values from `solve`.

**M5 — Projects and reports.** A project can be saved and opened. The same results can be shown as a short block report and as the detailed position report. The standard dual wheel can be placed from the screen.

## How a milestone is done

1. Agent 1 adds or extends the test and writes the behavior down in `docs/behavior.md`.
2. Agent 2 makes the solver test pass. The Fortran library is opened only for a number the layer method does not explain.
3. Agent 3 touches the screen only when the milestone names something a person sees. M1 through M3 stay on `run.bat`.
4. `py -m pytest` passes, and the milestone's line in this file moves under Done.
