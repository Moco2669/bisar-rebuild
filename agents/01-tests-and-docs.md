# Agent 1 — Tests and documentation

You extend the test suite and the short documents that describe behavior. You do not change `src/bisar/engine.py` except to import something the tests need.

## Read first

- `AGENTS.md` and the current milestone in `docs/ROADMAP.md`
- `docs/behavior.md` and `docs/solver-notes.md`
- `tests/test_inp.py`, `tests/test_report.py`, and the engine tests
- `D:\BISAR3\BISAR3.PDF` on this machine, as a checklist only. Do not copy its sentences into the repo.

The centerline, the standard dual wheel, interface slip, and the horizontal shear load already have fixtures and passing solver tests. Do not reopen them.

## What to add, for the milestone in the roadmap

1. A fixture in `tests/fixtures/` using the same record layout as `nrb1.inp`, and an expected-results JSON holding only numbers, when the milestone names a new calculation.
2. A test that parses the fixture and a solver test marked `pytest.mark.xfail(..., strict=True)` until Agent 2 makes it pass. When Agent 2 has made it pass, remove the mark in the same change that turns it green.
3. A short section in `docs/behavior.md`, in your own words, naming the manual section you used. Do not quote it.

## Oracle

When the original program can be run, write the input, run `BISAR.EXE` under otvdm, parse the detailed report with `bisar.report`, and store the printed numbers at four significant figures. Skip that live run when `D:\BISAR3` is absent. Committed fixtures must stand alone.

## Done

`pytest` passes, the new solver checks are strict xfails or genuine passes, and `git status` shows none of the original program's files.
