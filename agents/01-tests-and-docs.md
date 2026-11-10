# Agent 1 — Tests and documentation

You extend the test suite and the short documents that describe behavior. You do not change `src/bisar/engine.py` except to import something the tests need.

## Read first

- `AGENTS.md`
- `tests/test_inp.py`, `tests/test_report.py`, `tests/test_engine_oracle.py`
- `D:\BISAR3\BISAR3.PDF` on this machine, as a checklist only. Do not copy its sentences into the repo.

## What to add, in this order

1. Cases the manual treats as separate calculations: the standard dual wheel, a load with horizontal shear, and one interface whose shear-spring compliance is not zero.
2. For each case, an input fixture in `tests/fixtures/` using the same record layout as `nrb1.inp`, and an expected-results JSON holding only numbers.
3. A test that parses the fixture and a solver test marked `pytest.mark.xfail(..., strict=True)` until Agent 2 makes it pass. When Agent 2 has made it pass, remove the mark in the same change that turns it green.
4. A page in `docs/behavior.md` that lists, in your own words, the inputs and the reported quantities. Name the manual section you used. Do not quote it.

## Oracle

When the original program can be run, write the input, run `BISAR.EXE` under otvdm, parse the detailed report with `bisar.report`, and store the printed numbers at four significant figures. Skip that live run when `D:\BISAR3` is absent. Committed fixtures must stand alone.

## Done

`pytest` passes, the new solver checks are strict xfails or genuine passes, and `git status` shows none of the original program's files.
