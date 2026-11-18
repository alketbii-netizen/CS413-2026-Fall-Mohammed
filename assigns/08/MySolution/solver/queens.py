"""Python adapter for the LAMBDA3 CPS N-Queens solver (no HTTP, no browser).

The search logic lives entirely in ``queens_cps.lam``.  This module only
parses/type-checks that fixed file once, applies its ``queens_stream`` to a
board size, and forces stream cells one at a time with LAMBDA3's own
``lazy_eval`` primitive.  It never inspects closures; each event tuple is
converted to a JSON-ready dict.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAMBDA3 = _HERE.parent.parent / "LAMBDA3"
if str(_LAMBDA3) not in sys.path:
    sys.path.insert(0, str(_LAMBDA3))

import lambda3 as L  # noqa: E402

SOURCE = _HERE / "queens_cps.lam"
MIN_SIZE, MAX_SIZE = 4, 10
KINDS = ("try", "place", "reject", "backtrack", "solution", "done")


@lru_cache(maxsize=1)
def _program():
    """(queens_stream closure, safety_probe closure), type-checked once."""
    expr, _typ = L.d0exp_parse_and_typecheck(SOURCE.read_text())
    value = L.d0exp_evaluate(expr)
    return value.arg1[0], value.arg1[1]


def _apply(fn, arg):
    env = L.ENVcns("f", fn, L.ENVcns("x", arg, L.ENVnil()))
    return L.d0exp_evaluate(L.D0Eapp(L.D0Evar("f"), L.D0Evar("x")), env)


def _force(lazy):
    """Force one Strm cell with LAMBDA3's lazy_eval; returns a D0Vstcn."""
    env = L.ENVcns("s", lazy, L.ENVnil())
    return L.d0exp_evaluate(L.D0Eop1("lazy_eval", L.D0Evar("s")), env)


def _list(v) -> list[int]:
    out, items = [], v.arg1
    while isinstance(items, L.fnlist_cons):
        out.append(items.arg1.arg1)
        items = items.arg2
    return out


def board_rows(v) -> list[int]:
    """LAMBDA3 board (newest row first) -> columns in row order 0..r-1."""
    return list(reversed(_list(v)))


def event_to_json(v) -> dict:
    kind, column, row, board = v.arg1
    name = KINDS[kind.arg1]
    if name == "done":
        return {"event": "done"}
    if name == "solution":
        return {"event": "solution", "board": board_rows(board)}
    return {"event": name, "column": column.arg1, "row": row.arg1,
            "board": board_rows(board)}


def open_stream(size: int):
    """Return the unforced first cell (a LAMBDA3 Lazy value)."""
    if type(size) is not int or not MIN_SIZE <= size <= MAX_SIZE:
        raise ValueError(f"size must be an integer from {MIN_SIZE} to {MAX_SIZE}")
    stream_fn, _ = _program()
    return _apply(stream_fn, L.D0Vint(size))


def next_event(stream):
    """Force one cell: return (event_dict, tail) or (None, None) at the end."""
    cell = _force(stream)
    if not cell.is_cons:
        return None, None
    return event_to_json(cell.head), cell.tail


def is_forced(stream) -> bool:
    return bool(stream.evaluated)


def safe(column: int, rows: list[int]) -> bool:
    """Run the LAMBDA3 CPS safety checker; rows given in row order."""
    _, probe = _program()
    items = L.fnlist_nil()
    for c in rows:                       # newest row first
        items = L.fnlist_cons(L.D0Vint(c), items)
    arg = L.D0Vtupl((L.D0Vint(column), L.D0Vlist(items)))
    return _apply(probe, arg).arg1


def iterate(size: int):
    s = open_stream(size)
    while True:
        ev, s = next_event(s)
        if ev is None:
            return
        yield ev
