"""Command-line demonstration.

Run from assigns/06/:
    python3 MySolution/demo.py            # all demos, short term previews
    python3 MySolution/demo.py --full     # print full generated terms

For every example: source, generated pure term (preview; full text saved to
MySolution/generated/<ID>.txt), execution outcome + beta-value steps,
observation outcome + its separate steps, decoded answer, explicit expected
answer, and the source evaluator's answer for terminating examples.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from compiler import compile_expr                       # noqa: E402
from evaluator import evaluate, source_value_to_python  # noqa: E402
from examples import DEMOS, EX                          # noqa: E402
from observe import run_compiled                        # noqa: E402
from source_ast import show_source                      # noqa: E402
from target import is_pure, show, size                  # noqa: E402

EXEC_BUDGET = 100_000   # beta-value steps for running a compiled program
OBS_BUDGET = 100_000    # beta-value steps for observing (decoding) its value


def fmt(v) -> str:
    if v is True: return "true"
    if v is False: return "false"
    if isinstance(v, tuple): return "(" + ", ".join(fmt(x) for x in v) + ")"
    return str(v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="print full generated terms")
    ap.add_argument("--exec-budget", type=int, default=EXEC_BUDGET)
    ap.add_argument("--obs-budget", type=int, default=OBS_BUDGET)
    a = ap.parse_args()

    out_dir = HERE / "generated"
    out_dir.mkdir(exist_ok=True)
    print(f"Execution budget: {a.exec_budget} beta-value steps; "
          f"observation budget: {a.obs_budget} beta-value steps\n")
    passed = 0
    for id_, desc, src, kind, expected in DEMOS:
        term = compile_expr(src)
        text = show(term)
        (out_dir / f"{id_}.txt").write_text(text + "\n")
        r = run_compiled(term, kind, a.exec_budget, a.obs_budget)

        if r.exec_status == "exhausted":
            decoded = EX
            obs_line = "not observed (execution did not finish)"
        else:
            o = r.obs
            decoded = o.value if o.ok else o.status.upper()
            obs_line = f"{o.status}, {o.steps} steps"
        src_line = "skipped (divergent example)" if expected == EX else \
            fmt(source_value_to_python(evaluate(src).value))
        ok = (decoded == expected) and is_pure(term)
        passed += ok

        preview = text if a.full or len(text) <= 160 else text[:157] + "..."
        print(f"[{id_}] {desc}")
        print(f"  source        : {show_source(src)}")
        print(f"  pure term     : {preview}")
        print(f"                  ({size(term)} nodes, saved to MySolution/generated/{id_}.txt)")
        print(f"  execution     : {'value' if r.exec_status == 'value' else 'step-budget exhausted (not a proof of divergence)'}, {r.exec_steps} steps")
        print(f"  observation   : {obs_line}")
        print(f"  decoded       : {fmt(decoded) if decoded != EX else 'EXHAUSTED'}")
        print(f"  expected      : {fmt(expected) if expected != EX else 'EXHAUSTED'}")
        print(f"  source eval   : {src_line}")
        print(f"  result        : {'PASS' if ok else 'FAIL'}\n")
    print(f"{passed}/{len(DEMOS)} demonstrations match their expected answers.")
    return 0 if passed == len(DEMOS) else 1


if __name__ == "__main__":
    sys.exit(main())
