"""Desktop calculation window.

The layout follows the input panel: one system, with Loads, Layers, and
Positions. Each of those has a count. Modulus is shown in MPa, vertical and
horizontal loads in kN, and lengths in m. The draft keeps the solver's units
(Pa and m). Every displacement and stress in the results comes from ``solve``.
"""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk

from bisar.engine import solve
from bisar.model import Layer, Load, PointResult, Problem, QueryPoint

_MAX_COUNT = 20
_DEPTH_TOLERANCE = 1e-6
_DUAL_RADIUS = 0.105
_DUAL_LOAD_KN = 20.0
_DUAL_OFFSET = 0.1575

_MODE_LOAD_RADIUS = "2 - Load and Radius"
_MODE_STRESS_LOAD = "1 - Stress and Load"
_MODE_STRESS_RADIUS = "3 - Stress and Radius"
_LOAD_MODES = (_MODE_STRESS_LOAD, _MODE_LOAD_RADIUS, _MODE_STRESS_RADIUS)

_LOAD_COLUMNS = {
    _MODE_STRESS_LOAD: (
        ("vertical_stress", "Vertical\nStress\n(MPa)"),
        ("vertical_load", "Vertical\nLoad\n(kN)"),
        ("x", "X\nCoordinate\n(m)"),
        ("y", "Y\nCoordinate\n(m)"),
        ("horizontal_stress", "Horizontal\nStress\n(MPa)"),
        ("direction", "Shear\nDirection\n(deg.)"),
    ),
    _MODE_LOAD_RADIUS: (
        ("vertical_load", "Vertical\nLoad\n(kN)"),
        ("radius", "Radius\n(m)"),
        ("x", "X\nCoordinate\n(m)"),
        ("y", "Y\nCoordinate\n(m)"),
        ("horizontal_load", "Horizontal\nLoad\n(kN)"),
        ("direction", "Shear\nDirection\n(deg.)"),
    ),
    _MODE_STRESS_RADIUS: (
        ("vertical_stress", "Vertical\nStress\n(MPa)"),
        ("radius", "Radius\n(m)"),
        ("x", "X\nCoordinate\n(m)"),
        ("y", "Y\nCoordinate\n(m)"),
        ("horizontal_stress", "Horizontal\nStress\n(MPa)"),
        ("direction", "Shear\nDirection\n(deg.)"),
    ),
}

_BG = "#d4d0c8"
_HEADER = "#9ccfe0"
_FIELD = "#fff8c8"


class ScreenInputError(ValueError):
    """The window could not be turned into a calculation."""


@dataclass
class Draft:
    """One system, in the units the window stores for the solver."""

    name: str = "NRB-1"
    load_mode: str = _MODE_LOAD_RADIUS
    full_friction: bool = True
    compliance_kind: str = "reduced"
    layers: list[dict[str, str]] = field(default_factory=list)
    loads: list[dict[str, str]] = field(default_factory=list)
    points: list[dict[str, str]] = field(default_factory=list)


def sample_problem() -> Problem:
    """The recorded four-layer centerline, used as the window's starting structure."""
    return Problem(
        name="NRB-1",
        layers=(
            Layer(3.5e10, 0.35, 0.05, 0.0),
            Layer(2.8e9, 0.35, 0.15, 0.0),
            Layer(3.0e8, 0.35, 0.20, 0.0),
            Layer(1.0e8, 0.35, 0.0, 0.0),
        ),
        loads=(Load(7.0e5, 9.53654e-2, 0.0, 0.0, 0.0, 0.0),),
        points=tuple(
            QueryPoint(number, layer, 0.0, 0.0, depth)
            for number, (layer, depth) in enumerate(
                ((1, 0.0), (1, 1.0e-3), (1, 0.025), (2, 0.125), (3, 0.30), (4, 0.405)),
                start=1,
            )
        ),
    )


def sample_draft() -> Draft:
    return draft_from_problem(sample_problem())


def shown(value: float, scale: float) -> str:
    """Format one result the way the text report does, with noise printed as zero."""
    if abs(value) <= 1e-4 * max(abs(scale), 1e-30):
        value = 0.0
    return f"{value:.4E}"


def draft_from_problem(problem: Problem) -> Draft:
    return Draft(
        name=problem.name,
        layers=[
            {
                "modulus": _number(layer.modulus),
                "poisson": _number(layer.poisson),
                "thickness": _number(layer.thickness),
                "compliance": _number(layer.shear_spring),
            }
            for layer in problem.layers
        ],
        loads=[
            {
                "stress": _number(load.stress),
                "radius": _number(load.radius),
                "x": _number(load.x),
                "y": _number(load.y),
                "shear": _number(load.shear_stress),
                "direction": _number(load.shear_direction),
            }
            for load in problem.loads
        ],
        points=[
            {
                "layer": str(point.layer),
                "x": _number(point.x),
                "y": _number(point.y),
                "z": _number(point.z),
            }
            for point in problem.points
        ],
    )


def resize_draft(
    draft: Draft,
    *,
    layers: int | None = None,
    loads: int | None = None,
    positions: int | None = None,
) -> Draft:
    """Grow or shrink a table to the count typed in the window."""
    if layers is not None:
        draft.layers = _fit(draft.layers, layers, _blank_layer, "layers")
    if loads is not None:
        draft.loads = _fit(draft.loads, loads, _blank_load, "circular loads")
    if positions is not None:
        draft.points = _fit(draft.points, positions, _blank_point, "position entries")
    return draft


def calculate_draft(draft: Draft) -> tuple[tuple[PointResult, ...] | None, str | None]:
    try:
        results = solve(problem_from_draft(draft))
    except (ScreenInputError, ValueError, NotImplementedError) as exc:
        return None, str(exc)
    return results, None


def problem_from_draft(draft: Draft) -> Problem:
    if not draft.layers:
        raise ScreenInputError("Enter at least one layer.")
    if not draft.loads:
        raise ScreenInputError("Enter at least one load.")
    if not draft.points:
        raise ScreenInputError("Enter at least one position.")
    layers = tuple(_layer_from_row(index, row, draft) for index, row in enumerate(draft.layers, start=1))
    loads = tuple(_load_from_row(index, row) for index, row in enumerate(draft.loads, start=1))
    points = []
    for index, row in enumerate(draft.points, start=1):
        label = row.get("layer", "").strip()
        if "/" in label:
            raise ScreenInputError(
                f"Position {index} is on an interface. Select one layer, or both."
            )
        layer_number = _required_int(label, f"Position {index} layer")
        if not 1 <= layer_number <= len(layers):
            raise ScreenInputError(f"Position {index} layer {layer_number} is outside the structure.")
        points.append(
            QueryPoint(
                number=index,
                layer=layer_number,
                x=_required_float(row.get("x", ""), f"Position {index} X"),
                y=_required_float(row.get("y", ""), f"Position {index} Y"),
                z=_required_float(row.get("z", ""), f"Position {index} Z"),
            )
        )
    return Problem(name=draft.name.strip() or "untitled", layers=layers, loads=loads, points=tuple(points))


def infer_layer_label(depth: float, layers: list[dict[str, str]]) -> str:
    """Layer number at a depth. An interface is written as the two layer numbers."""
    if not layers:
        return ""
    top = 0.0
    for index, row in enumerate(layers[:-1], start=1):
        try:
            thickness = float(row.get("thickness") or "0")
        except ValueError:
            return ""
        bottom = top + thickness
        if depth < bottom - _DEPTH_TOLERANCE:
            return str(index)
        if abs(depth - bottom) <= _DEPTH_TOLERANCE:
            return f"{index}/{index + 1}"
        top = bottom
    return str(len(layers))


def shown_layer(point: dict[str, str], layers: list[dict[str, str]]) -> str:
    """Keep an explicit side of an interface; otherwise follow the depth."""
    try:
        depth = float(point.get("z", ""))
    except ValueError:
        return point.get("layer", "")
    inferred = infer_layer_label(depth, layers)
    stored = point.get("layer", "").strip()
    if "/" in inferred and stored.isdigit() and stored in inferred.split("/"):
        return stored
    return inferred or stored


def choose_layer(draft: Draft, index: int, choice: str) -> None:
    """Resolve one interface position: one side, or a row for each side."""
    if choice not in {"above", "below", "both"}:
        raise ScreenInputError("Select one layer, or both.")
    label = shown_layer(draft.points[index], draft.layers)
    if "/" not in label:
        raise ScreenInputError(f"Position {index + 1} is not on an interface.")
    above, below = label.split("/")
    point = draft.points[index]
    point["layer"] = above if choice in {"above", "both"} else below
    if choice == "both":
        copy = dict(point)
        copy["layer"] = below
        draft.points.insert(index + 1, copy)


def apply_standard_dual_loads(draft: Draft) -> None:
    """The two wheels of the standard axle: 20 kN, radius 0.105 m, 0.315 m apart."""
    draft.load_mode = _MODE_LOAD_RADIUS
    stress = _DUAL_LOAD_KN * 1000.0 / (math.pi * _DUAL_RADIUS**2)
    draft.loads = [_dual_load(-_DUAL_OFFSET, stress), _dual_load(_DUAL_OFFSET, stress)]


def apply_standard_positions(draft: Draft) -> None:
    """Positions between the two wheels and under the first wheel, at layer bottoms."""
    if len(draft.loads) < 2:
        raise ScreenInputError("The standard dual wheel needs two loads.")
    first, second = draft.loads[0], draft.loads[1]
    between = (
        (float(first["x"]) + float(second["x"])) / 2.0,
        (float(first["y"]) + float(second["y"])) / 2.0,
    )
    under = (float(first["x"]), float(first["y"]))
    bottoms = _layer_bottoms(draft.layers)
    if len(draft.layers) > 5:
        chosen = bottoms[:4]
        if bottoms[-1] not in chosen:
            chosen = [*chosen, bottoms[-1]]
    else:
        chosen = bottoms
    last_above = len(draft.layers) - 1
    points: list[dict[str, str]] = []
    for depth, above in chosen:
        sides = [above, above + 1] if above == last_above else [above]
        for layer in sides:
            for x_coord, y_coord in (between, under):
                points.append(
                    {
                        "layer": str(layer),
                        "x": _number(x_coord),
                        "y": _number(y_coord),
                        "z": _number(depth),
                    }
                )
    if not points:
        raise ScreenInputError("Enter the layer thicknesses before selecting positions.")
    if len(points) > _MAX_COUNT:
        raise ScreenInputError(f"Number of position entries must be a whole number from 1 to {_MAX_COUNT}.")
    draft.points = points


def display_load(row: dict[str, str], column: str) -> str:
    """One load cell in the units of the loads panel."""
    stress = _optional_float(row.get("stress", ""))
    shear = _optional_float(row.get("shear", ""))
    radius = _optional_float(row.get("radius", ""))
    if column == "vertical_stress":
        return "" if stress is None else _sci(stress / 1e6)
    if column == "horizontal_stress":
        return "" if shear is None else _sci(shear / 1e6)
    if column == "vertical_load":
        return "" if stress is None or radius is None else format(stress * math.pi * radius**2 / 1000.0, ".6g")
    if column == "horizontal_load":
        return "" if shear is None or radius is None else format(shear * math.pi * radius**2 / 1000.0, ".6g")
    return row.get(column, "")


def apply_load_display(row: dict[str, str], mode: str, shown_values: dict[str, str], written: dict[str, str]) -> None:
    """Write edited load cells back into stress, radius, and shear."""
    changed = {key for key, text in shown_values.items() if text.strip() != written.get(key, "").strip()}
    if not changed:
        return
    for key in ("x", "y", "direction"):
        if key in changed:
            row[key] = shown_values[key].strip()
    if mode == _MODE_LOAD_RADIUS and changed & {"vertical_load", "radius", "horizontal_load"}:
        radius = float(shown_values["radius"])
        if radius == 0.0:
            raise ScreenInputError("Load radius must be greater than zero.")
        row["radius"] = shown_values["radius"].strip()
        row["stress"] = _number(float(shown_values["vertical_load"]) * 1000.0 / (math.pi * radius**2))
        row["shear"] = _number(float(shown_values["horizontal_load"]) * 1000.0 / (math.pi * radius**2))
    elif mode == _MODE_STRESS_RADIUS and changed & {"vertical_stress", "radius", "horizontal_stress"}:
        row["radius"] = shown_values["radius"].strip()
        row["stress"] = _number(float(shown_values["vertical_stress"]) * 1e6)
        row["shear"] = _number(float(shown_values["horizontal_stress"]) * 1e6)
    elif mode == _MODE_STRESS_LOAD and changed & {"vertical_stress", "vertical_load", "horizontal_stress"}:
        stress = float(shown_values["vertical_stress"]) * 1e6
        if stress == 0.0:
            raise ScreenInputError("Load stress must be greater than zero.")
        radius = math.sqrt(float(shown_values["vertical_load"]) * 1000.0 / (math.pi * stress))
        row["stress"] = _number(stress)
        row["radius"] = _number(radius)
        row["shear"] = _number(float(shown_values["horizontal_stress"]) * 1e6)


def display_modulus(text: str) -> str:
    value = _optional_float(text)
    return "" if value is None else _sci(value / 1e6)


def display_compliance(text: str, kind: str, modulus: str, poisson: str) -> str:
    """Reduced compliance is metres. Standard compliance is the same spring in m³/N."""
    reduced = _optional_float(text)
    if reduced is None:
        return "" if text.strip() == "" else text
    if kind == "reduced":
        return _number(reduced)
    modulus_pa = float(modulus)
    ratio = float(poisson)
    return _compliance_text(reduced * (1.0 + ratio) / modulus_pa)


def store_compliance(text: str, kind: str, modulus: str, poisson: str) -> str:
    value = float(text)
    if kind == "reduced":
        return _number(value)
    modulus_pa = float(modulus)
    ratio = float(poisson)
    return _number(value * modulus_pa / (1.0 + ratio))


def run() -> int:
    """Open the calculation window until it is closed."""
    root = tk.Tk()
    CalculationWindow(root)
    root.mainloop()
    return 0


class CalculationWindow:
    """The input panel and the results that follow from it."""

    def __init__(self, root: tk.Tk, draft: Draft | None = None) -> None:
        self.root = root
        self.draft = draft or sample_draft()
        self._busy = False
        self.results_window: tk.Toplevel | None = None
        self.result_values: list[str] = []
        self.status = tk.StringVar()
        root.title(self.draft.name or "untitled")
        root.configure(bg=_BG)
        root.geometry("920x560")
        self._menus()
        self._header()
        self._tabs()
        self._footer()
        self.refresh()

    def refresh(self) -> None:
        self._busy = True
        try:
            self._sync_counts()
            self._render_loads()
            self._render_layers()
            self._render_positions()
            self.description.delete(0, "end")
            self.description.insert(0, self.draft.name)
            self.mode.set(self.draft.load_mode)
            self.friction.set(self.draft.full_friction)
            self.compliance_kind.set(self.draft.compliance_kind)
            self._show_compliance_choice()
        finally:
            self._busy = False

    def calculate(self) -> None:
        if self._busy:
            return
        try:
            self._pull()
            self._apply_counts()
        except ScreenInputError as exc:
            self.status.set(str(exc))
            return
        self.draft.name = self.description.get().strip() or "untitled"
        self.root.title(self.draft.name)
        results, error = calculate_draft(self.draft)
        if error is not None or results is None:
            self.status.set(error or "")
            self.result_values = []
            return
        self.status.set("")
        self._show_results(results)

    def widget_texts(self) -> list[str]:
        return _widget_texts(self.root)

    def _menus(self) -> None:
        menu = tk.Menu(self.root)
        results = tk.Menu(menu, tearoff=0)
        results.add_command(label="Calculate", command=self.calculate, accelerator="F5")
        menu.add_cascade(label="Results", menu=results)
        self.root.config(menu=menu)
        self.root.bind("<F5>", lambda _event: self.calculate())

    def _header(self) -> None:
        top = tk.Frame(self.root, bg=_BG)
        top.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(top, text="Number of Systems (1-10):", bg=_BG).pack(side="left")
        self.systems = tk.Spinbox(top, from_=1, to=10, width=4, command=self._reject_extra_systems)
        self.systems.pack(side="left", padx=6)
        self.systems.delete(0, "end")
        self.systems.insert(0, "1")
        system = tk.LabelFrame(self.root, text="", bg=_BG, padx=6, pady=4)
        system.pack(fill="both", expand=True, padx=8, pady=6)
        tab = tk.Label(system, text=" 1 ", bg=_BG, relief="raised", bd=2)
        tab.pack(anchor="w")
        description = tk.Frame(system, bg=_BG)
        description.pack(fill="x", pady=4)
        tk.Label(description, text="System Description:", bg=_BG).pack(side="left")
        self.description = tk.Entry(description)
        self.description.pack(side="left", fill="x", expand=True, padx=6)
        self.notebook = ttk.Notebook(system)
        self.notebook.pack(fill="both", expand=True)
        self.loads_tab = tk.Frame(self.notebook, bg=_BG)
        self.layers_tab = tk.Frame(self.notebook, bg=_BG)
        self.positions_tab = tk.Frame(self.notebook, bg=_BG)
        self.notebook.add(self.loads_tab, text="Loads")
        self.notebook.add(self.layers_tab, text="Layers")
        self.notebook.add(self.positions_tab, text="Positions")

    def _tabs(self) -> None:
        self._load_entries: list[dict[str, tk.Entry]] = []
        self._load_written: list[dict[str, str]] = []
        self._layer_entries: list[dict[str, tk.Entry]] = []
        self._layer_written: list[dict[str, str]] = []
        self._point_entries: list[dict[str, tk.Entry]] = []
        self._point_written: list[dict[str, str]] = []
        self._build_load_toolbar()
        self._build_layer_toolbar()
        self._build_position_toolbar()
        self.load_grid = tk.Frame(self.loads_tab, bg=_BG)
        self.load_grid.pack(fill="both", expand=True, pady=6)
        self.layer_grid = tk.Frame(self.layers_tab, bg=_BG)
        self.layer_grid.pack(fill="both", expand=True, pady=6)
        self.point_grid = tk.Frame(self.positions_tab, bg=_BG)
        self.point_grid.pack(fill="both", expand=True, pady=6)

    def _footer(self) -> None:
        footer = tk.Frame(self.root, bg=_BG)
        footer.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(footer, textvariable=self.status, bg=_BG, fg="#9b1c1c", anchor="w").pack(
            side="left", fill="x", expand=True
        )
        tk.Button(footer, text="Calculate", command=self.calculate, width=12).pack(side="right")

    def _build_load_toolbar(self) -> None:
        bar = tk.Frame(self.loads_tab, bg=_BG)
        bar.pack(fill="x")
        self.dual = tk.BooleanVar()
        tk.Checkbutton(
            bar,
            text="Use Standard Dual Wheel?",
            variable=self.dual,
            command=self._use_dual_wheel,
            bg=_BG,
        ).grid(row=0, column=0, sticky="w")
        self._save_retrieve(bar, row=0)
        tk.Label(bar, text="Mode of Load:", bg=_BG).grid(row=1, column=0, sticky="w", pady=4)
        self.mode = tk.StringVar(value=self.draft.load_mode)
        chooser = ttk.Combobox(bar, textvariable=self.mode, values=_LOAD_MODES, state="readonly", width=24)
        chooser.grid(row=1, column=1, sticky="w")
        chooser.bind("<<ComboboxSelected>>", self._change_mode)
        tk.Label(bar, text="No of Circular Loads (1-10):", bg=_BG).grid(row=1, column=2, sticky="e", padx=(16, 4))
        self.load_count = tk.Spinbox(bar, from_=1, to=_MAX_COUNT, width=4, command=self._resize_loads)
        self.load_count.grid(row=1, column=3, sticky="w")
        self.load_count.bind("<Return>", self._resize_loads)
        self.load_count.bind("<FocusOut>", self._resize_loads)

    def _build_layer_toolbar(self) -> None:
        bar = tk.Frame(self.layers_tab, bg=_BG)
        bar.pack(fill="x")
        self.friction = tk.BooleanVar(value=True)
        tk.Checkbutton(
            bar,
            text="Full Friction Between Layers?",
            variable=self.friction,
            command=self._toggle_friction,
            bg=_BG,
        ).grid(row=0, column=0, sticky="w")
        self._save_retrieve(bar, row=0)
        self.compliance_row = tk.Frame(bar, bg=_BG)
        self.compliance_row.grid(row=1, column=0, columnspan=2, sticky="w")
        self.compliance_kind = tk.StringVar(value="reduced")
        tk.Radiobutton(
            self.compliance_row,
            text="Standard Spring Compliance",
            variable=self.compliance_kind,
            value="standard",
            command=self._change_compliance_kind,
            bg=_BG,
        ).pack(side="left")
        tk.Radiobutton(
            self.compliance_row,
            text="Reduced Spring Compliance",
            variable=self.compliance_kind,
            value="reduced",
            command=self._change_compliance_kind,
            bg=_BG,
        ).pack(side="left")
        tk.Label(bar, text="No of Layers (1-10):", bg=_BG).grid(row=1, column=2, sticky="e", padx=(16, 4))
        self.layer_count = tk.Spinbox(bar, from_=1, to=_MAX_COUNT, width=4, command=self._resize_layers)
        self.layer_count.grid(row=1, column=3, sticky="w")
        self.layer_count.bind("<Return>", self._resize_layers)
        self.layer_count.bind("<FocusOut>", self._resize_layers)

    def _build_position_toolbar(self) -> None:
        bar = tk.Frame(self.positions_tab, bg=_BG)
        bar.pack(fill="x")
        tk.Button(
            bar,
            text="Select Positions for Standard Dual Wheel",
            command=self._select_positions,
        ).grid(row=0, column=0, sticky="w")
        self._save_retrieve(bar, row=0)
        tk.Label(bar, text="No of Position Entries (1-10):", bg=_BG).grid(row=1, column=2, sticky="e", padx=(16, 4))
        self.position_count = tk.Spinbox(bar, from_=1, to=_MAX_COUNT, width=4, command=self._resize_positions)
        self.position_count.grid(row=1, column=3, sticky="w", pady=4)
        self.position_count.bind("<Return>", self._resize_positions)
        self.position_count.bind("<FocusOut>", self._resize_positions)

    def _save_retrieve(self, bar: tk.Frame, row: int) -> None:
        buttons = tk.Frame(bar, bg=_BG)
        buttons.grid(row=row, column=4, sticky="e", padx=(12, 0))
        tk.Button(buttons, text="Save", width=8, command=self._not_stored).pack(side="left", padx=2)
        tk.Button(buttons, text="Retrieve", width=8, command=self._not_stored).pack(side="left", padx=2)

    def _render_loads(self) -> None:
        self._clear(self.load_grid)
        self._load_entries = []
        self._load_written = []
        columns = _LOAD_COLUMNS[self.draft.load_mode]
        self._header_cell(self.load_grid, 0, "Load\nNumber")
        for column, (_key, label) in enumerate(columns, start=1):
            self._header_cell(self.load_grid, column, label)
        for index, row in enumerate(self.draft.loads):
            tk.Label(self.load_grid, text=str(index + 1), bg=_FIELD, width=8, relief="ridge").grid(
                row=index + 1, column=0, padx=1, pady=1
            )
            entries: dict[str, tk.Entry] = {}
            written: dict[str, str] = {}
            for column, (key, _label) in enumerate(columns, start=1):
                text = display_load(row, key)
                entries[key] = self._cell(self.load_grid, index + 1, column, text)
                written[key] = text
            self._load_entries.append(entries)
            self._load_written.append(written)

    def _render_layers(self) -> None:
        self._clear(self.layer_grid)
        self._layer_entries = []
        self._layer_written = []
        columns = [("thickness", "Thickness\n(m)"), ("modulus", "Modulus of\nElasticity\n(MPa)"), ("poisson", "Poisson's\nRatio")]
        if not self.draft.full_friction:
            unit = "m³/N" if self.draft.compliance_kind == "standard" else "m"
            columns.append(("compliance", f"Spring\nCompliance\n({unit})"))
        self._header_cell(self.layer_grid, 0, "Layer\nNumber")
        for column, (_key, label) in enumerate(columns, start=1):
            self._header_cell(self.layer_grid, column, label)
        last = len(self.draft.layers) - 1
        for index, row in enumerate(self.draft.layers):
            tk.Label(self.layer_grid, text=str(index + 1), bg=_FIELD, width=8, relief="ridge").grid(
                row=index + 1, column=0, padx=1, pady=1
            )
            entries = {}
            written = {}
            for column, (key, _label) in enumerate(columns, start=1):
                text = self._layer_text(row, key, index == last)
                entry = self._cell(self.layer_grid, index + 1, column, text)
                if index == last and key in {"thickness", "compliance"}:
                    entry.configure(state="disabled")
                entries[key] = entry
                written[key] = text
            self._layer_entries.append(entries)
            self._layer_written.append(written)

    def _render_positions(self) -> None:
        self._clear(self.point_grid)
        self._point_entries = []
        self._point_written = []
        headers = (
            ("", "Position\nNumber"),
            ("x", "X\nCoordinate\n(m)"),
            ("y", "Y\nCoordinate\n(m)"),
            ("z", "Z (depth)\nCoordinate\n(m)"),
            ("layer", "Layer\nNo"),
        )
        for column, (_key, label) in enumerate(headers):
            self._header_cell(self.point_grid, column, label)
        for index, row in enumerate(self.draft.points):
            label = shown_layer(row, self.draft.layers)
            row["layer"] = label
            tk.Label(self.point_grid, text=str(index + 1), bg=_FIELD, width=10, relief="ridge").grid(
                row=index + 1, column=0, padx=1, pady=1
            )
            entries = {}
            written = {}
            for column, key in enumerate(("x", "y", "z"), start=1):
                text = row.get(key, "")
                entry = self._cell(self.point_grid, index + 1, column, text)
                if key == "z":
                    entry.bind("<FocusOut>", lambda _event, number=index: self._depth_changed(number))
                entries[key] = entry
                written[key] = text
            tk.Label(self.point_grid, text=label, bg=_FIELD, width=10, relief="ridge").grid(
                row=index + 1, column=4, padx=1, pady=1
            )
            if "/" in label:
                tk.Button(
                    self.point_grid,
                    text="Select Layer",
                    command=lambda number=index: self._select_layer(number),
                ).grid(row=index + 1, column=5, padx=4)
            self._point_entries.append(entries)
            self._point_written.append(written)

    def _pull(self) -> None:
        self._pull_loads()
        self._pull_layers()
        self._pull_points()
        self.draft.name = self.description.get().strip() or "untitled"
        self.draft.load_mode = self.mode.get()
        self.draft.full_friction = bool(self.friction.get())
        self.draft.compliance_kind = self.compliance_kind.get()

    def _pull_loads(self) -> None:
        for row, entries, written in zip(self.draft.loads, self._load_entries, self._load_written):
            shown_values = {key: entry.get() for key, entry in entries.items()}
            apply_load_display(row, self.draft.load_mode, shown_values, written)

    def _pull_layers(self) -> None:
        last = len(self.draft.layers) - 1
        for index, (row, entries, written) in enumerate(
            zip(self.draft.layers, self._layer_entries, self._layer_written)
        ):
            for key, entry in entries.items():
                if str(entry.cget("state")) == "disabled":
                    if key == "thickness":
                        row["thickness"] = "0"
                    continue
                typed = entry.get()
                if typed.strip() == written.get(key, "").strip():
                    continue
                if key == "modulus":
                    row["modulus"] = _number(float(typed) * 1e6)
                elif key == "compliance":
                    row["compliance"] = store_compliance(
                        typed,
                        self.draft.compliance_kind,
                        row.get("modulus", ""),
                        row.get("poisson", ""),
                    )
                else:
                    row[key] = typed.strip()
            if index == last:
                row["thickness"] = "0"

    def _pull_points(self) -> None:
        for row, entries, written in zip(self.draft.points, self._point_entries, self._point_written):
            for key, entry in entries.items():
                typed = entry.get()
                if typed.strip() != written.get(key, "").strip():
                    row[key] = typed.strip()
            row["layer"] = shown_layer(row, self.draft.layers)

    def _apply_counts(self) -> None:
        resize_draft(
            self.draft,
            layers=_count(self.layer_count.get(), "layers"),
            loads=_count(self.load_count.get(), "circular loads"),
            positions=_count(self.position_count.get(), "position entries"),
        )

    def _resize_loads(self, _event: object = None) -> None:
        self._resize("loads", self.load_count, "circular loads")

    def _resize_layers(self, _event: object = None) -> None:
        self._resize("layers", self.layer_count, "layers")

    def _resize_positions(self, _event: object = None) -> None:
        self._resize("positions", self.position_count, "position entries")

    def _resize(self, kind: str, spin: tk.Spinbox, label: str) -> None:
        if self._busy:
            return
        try:
            self._pull()
            count = _count(spin.get(), label)
        except (ScreenInputError, ValueError) as exc:
            self.status.set(str(exc))
            return
        self.status.set("")
        resize_draft(self.draft, **{kind: count})
        self._busy = True
        try:
            {"loads": self._render_loads, "layers": self._render_layers, "positions": self._render_positions}[kind]()
            self._sync_counts()
        finally:
            self._busy = False

    def _sync_counts(self) -> None:
        self._set_spin(self.load_count, len(self.draft.loads))
        self._set_spin(self.layer_count, len(self.draft.layers))
        self._set_spin(self.position_count, len(self.draft.points))

    def _change_mode(self, _event: object = None) -> None:
        if self._busy:
            return
        try:
            self._pull_loads()
        except (ScreenInputError, ValueError) as exc:
            self.mode.set(self.draft.load_mode)
            self.status.set(str(exc))
            return
        self.draft.load_mode = self.mode.get()
        self._busy = True
        try:
            self._render_loads()
        finally:
            self._busy = False

    def _toggle_friction(self) -> None:
        if self._busy:
            return
        try:
            self._pull_layers()
        except (ScreenInputError, ValueError) as exc:
            self.friction.set(self.draft.full_friction)
            self.status.set(str(exc))
            return
        self.draft.full_friction = bool(self.friction.get())
        self._show_compliance_choice()
        self._busy = True
        try:
            self._render_layers()
        finally:
            self._busy = False

    def _change_compliance_kind(self) -> None:
        if self._busy:
            return
        try:
            self._pull_layers()
        except (ScreenInputError, ValueError) as exc:
            self.compliance_kind.set(self.draft.compliance_kind)
            self.status.set(str(exc))
            return
        self.draft.compliance_kind = self.compliance_kind.get()
        self._busy = True
        try:
            self._render_layers()
        finally:
            self._busy = False

    def _show_compliance_choice(self) -> None:
        if self.draft.full_friction:
            self.compliance_row.grid_remove()
        else:
            self.compliance_row.grid()

    def _use_dual_wheel(self) -> None:
        if not self.dual.get() or self._busy:
            return
        try:
            self._pull()
        except (ScreenInputError, ValueError) as exc:
            self.dual.set(False)
            self.status.set(str(exc))
            return
        apply_standard_dual_loads(self.draft)
        self.mode.set(self.draft.load_mode)
        self.status.set("")
        self._busy = True
        try:
            self._render_loads()
            self._sync_counts()
        finally:
            self._busy = False

    def _select_positions(self) -> None:
        if self._busy:
            return
        try:
            self._pull()
            apply_standard_positions(self.draft)
        except (ScreenInputError, ValueError) as exc:
            self.status.set(str(exc))
            return
        self.status.set("")
        self._busy = True
        try:
            self._render_positions()
            self._sync_counts()
        finally:
            self._busy = False

    def _depth_changed(self, index: int) -> None:
        if self._busy:
            return
        try:
            self._pull_points()
        except (ScreenInputError, ValueError) as exc:
            self.status.set(str(exc))
            return
        self._busy = True
        try:
            self._render_positions()
        finally:
            self._busy = False

    def _select_layer(self, index: int) -> None:
        if self._busy:
            return
        try:
            self._pull_points()
        except (ScreenInputError, ValueError) as exc:
            self.status.set(str(exc))
            return
        label = shown_layer(self.draft.points[index], self.draft.layers)
        if "/" not in label:
            self.status.set(f"Position {index + 1} is not on an interface.")
            return
        above, below = label.split("/")
        choice = _ask_layer(self.root, above, below)
        if choice is None:
            return
        choose_layer(self.draft, index, choice)
        self.status.set("")
        self._busy = True
        try:
            self._render_positions()
            self._sync_counts()
        finally:
            self._busy = False

    def _reject_extra_systems(self) -> None:
        if self.systems.get() == "1":
            return
        self.systems.delete(0, "end")
        self.systems.insert(0, "1")
        self.status.set("Only one system is calculated.")

    def _not_stored(self) -> None:
        self.status.set("Saving and retrieving a project is not available yet.")

    def _show_results(self, results: tuple[PointResult, ...]) -> None:
        if self.results_window is not None and self.results_window.winfo_exists():
            self.results_window.destroy()
        window = tk.Toplevel(self.root)
        window.title("Results")
        window.geometry("980x320")
        window.configure(bg=_BG)
        self.results_window = window
        columns = ("position", "layer", "ux", "uy", "uz", "xx", "yy", "zz", "yz", "xz", "xy")
        headings = (
            "Position",
            "Layer",
            "UX (m)",
            "UY (m)",
            "UZ (m)",
            "XX (Pa)",
            "YY (Pa)",
            "ZZ (Pa)",
            "YZ (Pa)",
            "XZ (Pa)",
            "XY (Pa)",
        )
        tree = ttk.Treeview(window, columns=columns, show="headings", height=12)
        for column, heading in zip(columns, headings):
            tree.heading(column, text=heading)
            tree.column(column, width=88, anchor="e")
        self.result_values = []
        for result in results:
            displacement = result.total_displacement
            stress = result.total_stress
            if displacement is None or stress is None:
                continue
            values = (
                str(result.position),
                str(result.layer),
                shown(displacement.x, displacement.z),
                shown(displacement.y, displacement.z),
                shown(displacement.z, displacement.z),
                shown(stress.xx, stress.zz),
                shown(stress.yy, stress.zz),
                shown(stress.zz, stress.zz),
                shown(stress.yz, stress.zz),
                shown(stress.xz, stress.zz),
                shown(stress.xy, stress.zz),
            )
            tree.insert("", "end", values=values)
            self.result_values.extend(values)
        tree.pack(fill="both", expand=True, padx=8, pady=8)

    def _layer_text(self, row: dict[str, str], key: str, base: bool) -> str:
        if key == "thickness":
            return "" if base else row.get("thickness", "")
        if key == "modulus":
            return display_modulus(row.get("modulus", ""))
        if key == "compliance":
            return display_compliance(
                row.get("compliance", ""),
                self.draft.compliance_kind,
                row.get("modulus", ""),
                row.get("poisson", ""),
            )
        return row.get(key, "")

    def _header_cell(self, grid: tk.Frame, column: int, text: str) -> None:
        tk.Label(grid, text=text, bg=_HEADER, relief="ridge", width=12, justify="center").grid(
            row=0, column=column, padx=1, pady=1, sticky="nsew"
        )

    def _cell(self, grid: tk.Frame, row_index: int, column: int, text: str) -> tk.Entry:
        entry = tk.Entry(grid, width=14, justify="right", bg="white", relief="sunken")
        entry.insert(0, text)
        entry.grid(row=row_index, column=column, padx=1, pady=1)
        return entry

    def _clear(self, frame: tk.Frame) -> None:
        for child in frame.winfo_children():
            child.destroy()

    def _set_spin(self, spin: tk.Spinbox, value: int) -> None:
        spin.delete(0, "end")
        spin.insert(0, str(value))


def _dual_load(y_coord: float, stress: float) -> dict[str, str]:
    return {
        "stress": _number(stress),
        "radius": _number(_DUAL_RADIUS),
        "x": "0",
        "y": _number(y_coord),
        "shear": "0",
        "direction": "0",
    }


def _layer_bottoms(layers: list[dict[str, str]]) -> list[tuple[float, int]]:
    depth = 0.0
    bottoms = []
    for index, row in enumerate(layers[:-1], start=1):
        depth += float(row.get("thickness") or "0")
        bottoms.append((depth, index))
    return bottoms


def _layer_from_row(index: int, row: dict[str, str], draft: Draft) -> Layer:
    base = index == len(draft.layers)
    thickness = 0.0 if base else _required_float(row.get("thickness", ""), f"Layer {index} thickness")
    if draft.full_friction or base:
        compliance = 0.0
    else:
        compliance = _required_float(row.get("compliance", ""), f"Layer {index} shear-spring compliance")
    return Layer(
        modulus=_required_float(row.get("modulus", ""), f"Layer {index} modulus"),
        poisson=_required_float(row.get("poisson", ""), f"Layer {index} Poisson's ratio"),
        thickness=thickness,
        shear_spring=compliance,
    )


def _load_from_row(index: int, row: dict[str, str]) -> Load:
    return Load(
        stress=_required_float(row.get("stress", ""), f"Load {index} vertical stress"),
        radius=_required_float(row.get("radius", ""), f"Load {index} radius"),
        x=_required_float(row.get("x", ""), f"Load {index} X"),
        y=_required_float(row.get("y", ""), f"Load {index} Y"),
        shear_stress=_required_float(row.get("shear", ""), f"Load {index} shear stress"),
        shear_direction=_required_float(row.get("direction", ""), f"Load {index} direction"),
    )


def _blank_layer() -> dict[str, str]:
    return {"modulus": "", "poisson": "0.35", "thickness": "", "compliance": "0"}


def _blank_load() -> dict[str, str]:
    return {"stress": "", "radius": "", "x": "0", "y": "0", "shear": "0", "direction": "0"}


def _blank_point() -> dict[str, str]:
    return {"layer": "", "x": "0", "y": "0", "z": ""}


def _fit(rows: list[dict[str, str]], count: int, blank, label: str) -> list[dict[str, str]]:
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= _MAX_COUNT:
        raise ScreenInputError(f"Number of {label} must be a whole number from 1 to {_MAX_COUNT}.")
    updated = [dict(row) for row in rows[:count]]
    while len(updated) < count:
        updated.append(blank())
    return updated


def _count(text: str, label: str) -> int:
    try:
        number = float(text.strip())
    except ValueError:
        raise ScreenInputError(f"Number of {label} must be a whole number from 1 to {_MAX_COUNT}.") from None
    if not number.is_integer():
        raise ScreenInputError(f"Number of {label} must be a whole number from 1 to {_MAX_COUNT}.")
    count = int(number)
    if not 1 <= count <= _MAX_COUNT:
        raise ScreenInputError(f"Number of {label} must be a whole number from 1 to {_MAX_COUNT}.")
    return count


def _ask_layer(parent: tk.Misc, above: str, below: str) -> str | None:
    result: dict[str, str | None] = {"value": None}
    dialog = tk.Toplevel(parent)
    dialog.title("Select required layer")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.configure(bg=_BG)
    var = tk.StringVar(value="both")
    tk.Label(dialog, text="Select required layer", bg=_BG).pack(anchor="w", padx=12, pady=(10, 4))
    for text, value in (
        (f"Layers {above} and {below}", "both"),
        (f"Layer {above} only", "above"),
        (f"Layer {below} only", "below"),
    ):
        tk.Radiobutton(dialog, text=text, variable=var, value=value, bg=_BG).pack(anchor="w", padx=16)
    buttons = tk.Frame(dialog, bg=_BG)
    buttons.pack(pady=8)

    def accept() -> None:
        result["value"] = var.get()
        dialog.destroy()

    tk.Button(buttons, text="Ok", width=8, command=accept).pack(side="left", padx=4)
    tk.Button(buttons, text="Cancel", width=8, command=dialog.destroy).pack(side="left", padx=4)
    dialog.wait_window()
    return result["value"]


def _widget_texts(widget: tk.Misc) -> list[str]:
    found = []
    try:
        found.append(str(widget.cget("text")))
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        found.extend(_widget_texts(child))
    return found


def _required_float(text: str, label: str) -> float:
    try:
        return float(str(text).strip())
    except ValueError:
        raise ScreenInputError(f"{label} must be a number.") from None


def _required_int(text: str, label: str) -> int:
    number = _required_float(text, label)
    if not number.is_integer():
        raise ScreenInputError(f"{label} must be a whole number.")
    return int(number)


def _optional_float(text: str) -> float | None:
    if str(text).strip() == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _number(value: float) -> str:
    return format(value, ".8g")


def _sci(value: float) -> str:
    return f"{value:.4E}"


def _compliance_text(value: float) -> str:
    """Two digits after the leading one, with halves rounded away from zero."""
    if value == 0.0:
        return "0.00E+00"
    sign = "-" if value < 0.0 else ""
    magnitude = abs(value)
    exponent = math.floor(math.log10(magnitude))
    mantissa = math.floor(magnitude / 10**exponent * 100 + 0.5) / 100
    if mantissa >= 10:
        mantissa /= 10
        exponent += 1
    return f"{sign}{mantissa:.2f}E{exponent:+03d}"
