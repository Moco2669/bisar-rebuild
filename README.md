# BISAR rebuild

A Python program for stresses, strains, and displacements in a layered elastic pavement. Results are checked against BISAR-PC 2.0.

The calculation input is the record layout used by `DUMMY.INP`: layers (modulus, Poisson's ratio, thickness, interface shear spring), circular loads, and the positions where a response is required. The first recorded case is the four-layer centerline in `tests/fixtures/nrb1.inp`.

```powershell
py -m pip install -e ".[dev]"
py -m pytest
```

That run checks the bonded centerline, the standard dual wheel, interface slip, the horizontal shear load, and the calculation window.

`run.bat` opens the calculation window. `run.bat tests\fixtures\nrb1.inp` still prints that case.

Milestones are in `docs/ROADMAP.md`. The current one is saving a project and the two reports. Three agents share each milestone. Their prompts are in `agents/`, and the order they run is in `AGENTS.md`.

The Shell manual and the original program stay in `D:\BISAR3` on the machine that has them. They are not part of this repository.
