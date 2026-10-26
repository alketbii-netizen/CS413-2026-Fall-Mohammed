# CS413 Midterm 1 — Compiling Extended LAMBDA into Pure Lambda-Calculus

Mohammed Alketbi — `assigns/06/MySolution/`

## Requirements

- Python **3.12 or later** (developed and tested with 3.13).
- No third-party packages; standard library only (`unittest`, `dataclasses`).
- Uses the supplied, unmodified `assigns/05/lambda1_vp.py` (imported via `source_ast.py`).

## Commands (run from `assigns/06/`)

```bash
# setup: nothing to install
python3 --version                                        # must be >= 3.12

# tests (53 unittest cases)
python3 -m unittest discover -s MySolution -t MySolution -v

# demonstration: all mandatory examples + one nested pair
python3 MySolution/demo.py
python3 MySolution/demo.py --full                        # print whole generated terms
python3 MySolution/demo.py --exec-budget 5000 --obs-budget 5000
```

`demo.py` exits with status 0 only if every demonstration matches its explicit
expected answer. Each generated pure term is also saved to
`MySolution/generated/<ID>.txt`.

## Modules

| Module | Role |
| --- | --- |
| `source_ast.py` | Imports the supplied source AST / `D0ExpVisitor`; example-building helpers; source printer. |
| `target.py` | Target AST `Var` / `Lam` / `App` (immutable), printer, free variables, fresh names, capture-avoiding substitution, alpha-equivalence, purity check. |
| `church.py` | Church-encoding library: booleans, numerals, SUCC/PRED/ISZERO, ADD/SUB/MUL, comparisons, NOT, pairs, Z. Every combinator is closed. |
| `compiler.py` | `compile_expr(source) -> Term`, a `D0ExpVisitor`. Does not import the evaluator. |
| `evaluator.py` | The single shared evaluator `evaluate(e, budget)`: bounded weak call-by-value for target terms; call-by-value source semantics for source ASTs. Does not import the compiler. |
| `observe.py` | Bounded observers (natural, boolean, pair) and `run_compiled` (execute + observe). |
| `examples.py` | Mandatory demonstration programs built as source ASTs. |
| `demo.py` | Command-line demonstration. |
| `tests/` | `unittest` suite (`test_target`, `test_church`, `test_compiler`, `test_observe`). |

## Budgets

| Budget | Value | Used for |
| --- | --- | --- |
| Execution | 100,000 beta-value steps | Running a compiled program to a value |
| Observation | 100,000 beta-value steps | Decoding (STEP/BASE spine, boolean markers, pair projections) |
| Divergence tests | 5,000 steps | Tests that expect exhaustion (keeps the suite fast) |

The largest terminating demo (`fib 5`) needs 2,518 execution steps and 45
observation steps; `fact 4` needs 471 and 218. So the defaults leave a wide
margin. Divergent examples (`LOOP`, `(lam x. 0) LOOP`) report
**step-budget exhausted** after exactly 100,000 steps; this is reported as
exhaustion, not as proof of nontermination.

## Statuses and diagnostics

- `evaluate(term, budget)` returns `EvalResult(status, value, steps)` with
  status `"value"` or `"exhausted"`. Open target terms raise `OpenTermError`
  (target execution is restricted to closed terms); a negative budget raises
  `ValueError`. Source ASTs return their source value (status `"value"`, 0 steps);
  source runtime errors raise `SourceError`.
- Observers return `ObsResult(status, value, steps)` with status `"ok"`,
  `"exhausted"` (observation budget) or `"malformed"` (output is not a valid
  spine / boolean marker).
- `compile_expr` raises `CompileError` naming the unsupported literal or
  operator (e.g. `unsupported binary operator '/'`).

## Limitations

- No parser; programs are built as Python ASTs (allowed by the assignment).
- No static type checking: ill-typed programs compile, and their observation
  may be `malformed` or meaningless.
- The reducer is substitution-based and not optimized; Church arithmetic is
  unary, so large numbers (e.g. `fact 6`) take many steps.
- Target execution accepts closed terms only (compilation and substitution
  work on open terms).
- Exhaustion is not a proof of divergence.

## Presentation

- Slides (PDF): `MySolution/slides/CS413-Midterm1-Slides.pdf` (source: `slides/make_slides.py`)
- Recording: **TODO — add link here** (e.g. a BU OneDrive/YouTube unlisted link set to
  "anyone with the link can view"; verify it opens in a private window).

## Attribution

- Substitution and fresh-name scheme adapted from my Assignment 5 solution
  (`assigns/05/MySolution/lambda1_visitors.py`).
- Church numerals/booleans: Church (1941); pair-based predecessor (Kleene) and
  the call-by-value fixed-point combinator Z as presented in Pierce,
  *Types and Programming Languages* (2002), Ch. 5.
- AI assistance is documented in `AI-TRANSCRIPT.md`.
