import sys
from pathlib import Path

SOL = Path(__file__).resolve().parent.parent
if str(SOL) not in sys.path:
    sys.path.insert(0, str(SOL))

from compiler import compile_expr  # noqa: E402
from observe import run_compiled    # noqa: E402

EXEC = 100_000
OBS = 100_000
DIVERGE_BUDGET = 5_000


def run(src, kind, exec_budget=EXEC, obs_budget=OBS):
    """Compile + execute + observe; return decoded value or 'EXHAUSTED'."""
    r = run_compiled(compile_expr(src), kind, exec_budget, obs_budget)
    if r.exec_status == "exhausted":
        return "EXHAUSTED"
    assert r.obs is not None and r.obs.ok, r.obs
    return r.obs.value
