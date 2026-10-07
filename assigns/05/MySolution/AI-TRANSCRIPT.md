# AI-TRANSCRIPT

**AI tool used:** Claude (Anthropic), in a session with a Linux shell where it
could read the class repository, run Python 3.12.3 and install pytest. All
code, tests and documents in this directory were written by Claude at the
student's request; the student chose the assignment and directed the work.

## Prompts and what was done

1. **Request:** "now lets do the new assignment 5". Claude pulled the current
   class repository and read `assigns/05/Assign05.md` in full (the file ends
   with the Evaluation table, so it was not truncated), the supplied
   `lambda1_vp.py`, and the supplied tests and `cases.json` under `TEST/`, to
   see the visitor interface and how the supplied tests import the code.
2. **Design (Claude's suggestions, adopted):**
   - one `SubstitutionVisitor` that carries the target, the replacement, the
     replacement's free variables and one shared "used names" set;
   - alpha-renaming implemented as a substitution of the old name by a fresh
     variable using the same visitor class, so no separate renamer or string
     replacement is needed and inner shadowing is handled by the binding rules;
   - renaming only when the target is free in the binder's body and the binder
     name is free in the replacement (the assignment asks to avoid unnecessary
     renaming);
   - for `fix`, rename the parameter before the function name, so the case
     where both have the same name keeps the evaluator's behavior;
   - a small `CanonicalFormVisitor` (alpha-equivalence by binder depth), so
     tests can compare results independently of the fresh-name policy.
3. **Tests:** the expected results for about 40 substitution cases and 30
   printing cases were worked out by hand from the assignment text before
   running anything, then compared with the program. Both suites share those
   cases and checks (`TEST/shared_cases.py`), but each runs on its own.

## Problems found while working

- A leftover helper method that only raised `NotImplementedError` was found in
  the first draft of `CanonicalFormVisitor` and removed.
- The first draft of one pretty-printing test used a string `.replace()` to fix
  up its own expected value; it was rewritten as a plain literal.
- A stray assignment expression in a test constant was removed.
- Mutation testing (below) showed that one of Claude's own mutants was
  mis-specified (it added a hidden attribute that dataclass equality ignores) and
  another was equivalent to the original code (the target name is always already
  in the used set whenever a rename can happen, so adding it explicitly is
  redundant but harmless). The first was replaced by a mutant that modifies the
  input in place, which the tests do catch.

## How the output was checked

- Both documented commands were run from a clean copy of `assigns/05` (the
  class repository's files plus `MySolution/`): 39 `unittest` tests and 274
  `pytest` tests pass, also when started from a different directory.
- **Mutation testing.** Claude made 29 deliberately wrong versions of
  `lambda1_visitors.py`: no renaming (capture), shadowing ignored, `let`
  initializer treated as bound, each `fix` binder not renamed or not shadowing,
  fresh names that collide with existing, earlier-generated or replacement
  names, renaming that ignores shadowing, the replacement substituted again, input
  trees modified in place, wrong printing formats, a dropped pair component, and
  evaluation during substitution. Both suites fail on 28 of the 29; the one that
  survives is the equivalent mutant described above.
- **Independent oracle.** A property test evaluates `e[x := r]` and `e` with `x`
  bound to the value of `r`, in an environment that binds every name, on 1,500
  random well-typed terms. A capture bug changes the result. The supplied
  evaluator is used only in tests, never by the visitors.
- The free-variable property `FV(e[x := r]) = (FV(e) - {x}) union FV(r)` is
  checked on named examples and on 1,500 random terms of every constructor
  (including terms where `x` is not free, which must come back unchanged).
- A test counts calls to `accept`, and a source check confirms the visitors use
  no `isinstance`, tag tests or `match` statements.
- The supplied files were compared with the class repository and are unchanged.

## What was not relied on

Expected outputs come from the assignment's own table and hand derivation, not
from running the implementation and copying its output. The README's
design explanation (441 words) and limitations describe the code as written;
the 4300-digit limit was confirmed by running Python.
