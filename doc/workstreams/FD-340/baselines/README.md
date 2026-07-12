# FD-340 Golden Baselines — PyQt5 build (pre-PySide6 migration)

Captured **2026-07-11** from the PyQt5 build at `/Users/patrick/worktrees/FD-340/familydiagram`.
These are the measurements the PySide6 migration is graded against. All raw data.

Build under test: **PyQt5 5.15.11 / Qt runtime 5.15.2 / Python 3.11.6**, native extension
`_pkdiagram.cpython-311-darwin.so` (from `/Users/patrick/theapp/.venv`, ABI-identical, not rebuilt).

Common invocation prefix (all commands below):
```
cd /Users/patrick/worktrees/FD-340/familydiagram && \
PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/patrick/theapp/.venv uv run --no-sync <cmd>
```
`--no-sync` + `UV_PROJECT_ENVIRONMENT` reuse the origin's proven venv; `PYTHONDONTWRITEBYTECODE=1`
prevents writing any `.pyc` into the origin clone. No files in the origin tree were modified.

## Files

| File | Captures | Command that produced it |
|------|----------|--------------------------|
| `collection-baseline.json` | Per-test-file collected test counts + total (1226 tests, 110 files, 2 skipped at collection). | `pytest --collect-only -q -o addopts=""` (node ids parsed into per-file counts) |
| `suite-baseline.json` | Full unit-suite result: pass/fail/error counts per file + totals, plus the list of already-failing/erroring tests (pre-existing; migration is not to be blamed for these). Serial run (no xdist, to avoid Qt-parallel flakiness contaminating the failing set). | `pytest --junit-xml=junit.xml -p no:cacheprovider` (addopts `-vv --disable-warnings` etc. from `pytest.ini` retained; junit parsed) |
| `ext-goldens.json` | Compiled `_pkdiagram` extension: every enum name+value (custom: `OperatingSystem`, `FileStatus`; plus Qt-inherited enums re-exposed by `PathItemBase`), and geometry-helper outputs (`distance`, `pointOnRay`, `perpendicular`, `splineFromPoints`, `splineFromPoints2`, `strokedPath`) over a fixed grid of representative inputs. Inputs recorded alongside outputs; floats at full `repr` precision; `QPainterPath` outputs serialized as element `(type,x,y)` sequences. | `python gen_ext.py` (see `notes` block in the JSON for signatures) |
| `pickle-baseline.json` | For the three fixtures below: byte `sha256`, the true GLOBAL reduce callables, and the Qt types reconstructed via `sip._unpickle_type`. Captured by instrumenting `pickle.Unpickler.find_class` over a real `load()` of each fixture. | `python gen_pickle.py` |

### Extension goldens — signatures (for the migration to match)
- `distance(p1:QPointF, p2:QPointF) -> float`
- `pointOnRay(orig:QPointF, dest:QPointF, distance:float) -> QPointF`
- `perpendicular(pointA:QPointF, pointB:QPointF, width:float, reverse:bool=False) -> QPointF`
- `splineFromPoints(list[QPointF]) -> QPainterPath`
- `splineFromPoints2(list[QPointF]) -> QPainterPath`
- `strokedPath(path:QPainterPath, pen:QPen) -> QPainterPath`

### Pickle fixtures covered
- `pkdiagram/tests/data/v114a7_simplefamily.pickle`
- `pkdiagram/tests/data/stale-refs.fd/diagram.pickle`
- `pkdiagram/resources/Legend-Scene.fd/diagram.pickle`

Finding: the only GLOBAL reduce callable in each fixture is `sip._unpickle_type` (module stored as
bare `sip`, resolved as `PyQt5.sip` in this build). Qt types are embedded as **string arguments** to
`sip._unpickle_type`, not as GLOBAL opcodes — the reconstructed set is `QDate`, `QPointF`, `QSize`
(QtCore) and `QColor` (QtGui). (The task's expected list named `QPointF` and `QColor`; `QDate` and
`QSize` are also present.) PySide6 pickles Qt types under a different reduce path, so both the byte
`sha256` and the reconstructed-type set are load-bearing for the migration.
