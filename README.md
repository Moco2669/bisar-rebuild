# BISAR rebuild

A Python program for stresses, strains, and displacements in a layered elastic pavement. Results are checked against BISAR-PC 2.0.

The calculation input is the record layout used by `DUMMY.INP`: layers (modulus, Poisson's ratio, thickness, interface shear spring), circular loads, and the positions where a response is required. The first recorded case is the four-layer centerline in `tests/fixtures/nrb1.inp`.

```powershell
py -m pip install -e ".[dev]"
py -m pytest
```

That run checks the bonded centerline, the standard dual wheel, interface slip, and a horizontal shear load.

Milestones are in `docs/ROADMAP.md`. The current one is a calculation screen. Three agents share each milestone. Their prompts are in `agents/`, and the order they run is in `AGENTS.md`.

The Shell manual and the original program stay in `D:\BISAR3` on the machine that has them. They are not part of this repository.
