# Assignment 5: Pretty printing and capture-avoiding substitution with visitors

Both operations are visitors over the supplied `../lambda1_vp.py`. Nothing in
the supplied files was changed.

## Python version and setup

Python **3.12 or later** (the supplied code uses the `type` alias syntax).
Tested with Python 3.12.3 and pytest 9.1.1. `unittest` is in the standard
library; pytest is the only extra package:

```sh
python3.12 -m pip install pytest
```

## Files

| File | Purpose |
| --- | --- |
| `lambda1_visitors.py` | `PrettyPrintVisitor`, `SubstitutionVisitor`, the entry points `d0exp_pretty` and `d0exp_substitute`, and two helper visitors (`NameCollectorVisitor`, `CanonicalFormVisitor`) |
| `TEST/test_unittest_visitors.py` | the `unittest` suite (`unittest.TestCase` classes) |
| `TEST/test_pytest_visitors.py` | the `pytest` suite (test functions and plain `assert`) |
| `TEST/shared_cases.py` | example inputs, hand-derived expected results and checks used by both suites |
| `AI-TRANSCRIPT.md` | AI use and how its output was checked |

## Running the tests

Run each suite on its own, from the assignment directory `assigns/05`:

```sh
python3.12 -m unittest discover -s MySolution/TEST -p 'test_unittest_*.py' -v
python3.12 -m pytest MySolution/TEST/test_pytest_visitors.py -v
```

The first runs 39 tests, the second 274 (parametrized cases count separately).
Each takes under a second, and each returns a nonzero exit status on failure.

## API and examples

```python
from lambda1_visitors import d0exp_pretty, d0exp_substitute   # from MySolution/

d0exp_pretty(expression)                         # -> str
d0exp_substitute(expression, "x", replacement)   # -> new expression
```

`lambda1_visitors.py` puts `assigns/05` on `sys.path` itself, so it finds the
supplied `lambda1_vp.py` wherever Python is started. Expressions are the supplied classes, for example
`D0Eapp(D0Elam("x", D0Eop2("+", D0Evar("x"), D0Eint(1))), D0Eint(4))`, which
prints as `((lam x. (x + 1)) 4)`.

| Expression | Substitution | Result |
| --- | --- | --- |
| `(lam y. (x + y))` | `x := y` | `(lam y_1. (y + y_1))` |
| `(let y = x in (x + y))` | `x := y` | `(let y_1 = y in (y + y_1))` |
| `(let x = x in (x + y))` | `x := 3` | `(let x = 3 in (x + y))` |
| `(fix f(n). (x + (f n)))` | `x := f` | `(fix f_1(n). (f + (f_1 n)))` |
| `(fix f(n). (x + (f n)))` | `x := (f + n)` | `(fix f_1(n_1). ((f + n) + (f_1 n_1)))` |

The visitors can also be used directly: `expression.accept(PrettyPrintVisitor())`
and `expression.accept(SubstitutionVisitor.for_expression(expression, "x", r))`.

## Fresh-name policy

A binder `b` that must be renamed becomes `b_1`, or `b_2`, `b_3`, ... : the
first name of that form that is not in the **used set**. The used set holds
every variable occurrence and every binder name (free or bound) of the
expression and of the replacement, plus the substitution target. Every name
generated is added to it, so it is never generated twice in one call. A new set
is built for each call, so the same call always gives the same result.
Free-variable names alone would not be enough: a fresh name must also differ
from names that are bound somewhere in the expression or the replacement.

A binder is renamed only if the target occurs free in its body **and** the
binder's name occurs free in the replacement. Otherwise the binder is kept.

## Design explanation

**Result types.** The supplied `D0ExpVisitor[R]` is generic in its result type,
so each operation fixes `R`. `PrettyPrintVisitor` is a `D0ExpVisitor[str]`: each
method returns the text of its node, built from the text of its children.
`SubstitutionVisitor` is a `D0ExpVisitor[d0exp]`: each method returns a new
expression. The helpers have their own types: `NameCollectorVisitor` returns a
set of names, and `CanonicalFormVisitor` returns a string used to compare
expressions up to alpha-equivalence. None of them evaluates anything; they only
walk the tree through `accept`.

**Context in substitution.** A `SubstitutionVisitor` is built with the context
of one call: the target variable, the replacement, the free variables of the
replacement (computed once with the supplied `d0exp_fvset`), and the used set
of names. Every `visit_` method reads this context. The used set is shared by
all visitors created during the call and grows as fresh names are made, which
is what keeps a name generated earlier from being generated again.

**Scope and renaming.** At a binder the visitor asks two questions. Is the
target bound here (for `fix`, by either binder)? Does the target occur free in
the body at all? If the target is bound, or does not occur, the binder is
returned unchanged, so nothing is renamed when no substitution can happen.
Otherwise, if the binder's name occurs free in the replacement, the binder
would capture it, so the binder is renamed. Renaming is itself a substitution of
the old name by a variable with the new name, done by another
`SubstitutionVisitor` that shares the used set. Because it replaces only free
occurrences, an inner binder with the same name stops it, which gives correct
nested shadowing. Because the new name occurs nowhere else, that inner
substitution can never capture anything. For `let`, the initializer is visited
without any renaming and only the body is renamed. For `fix`, the parameter is
renamed before the function name: when both have the same name the parameter
shadows the function name, as in the supplied evaluator, and this order keeps
that behavior.

**Operation versus constructor.** A new operation is one new visitor class with
a method for each existing constructor; no existing class changes. This is how
`PrettyPrintVisitor` was added without touching `lambda1_vp.py`. A new
constructor is the reverse: it needs a new expression class with its own
`accept`, a new abstract method in `D0ExpVisitor`, and a new method in every
existing visitor (the supplied evaluator, the supplied free-variable visitor,
and all of mine). Until every visitor is updated, the abstract method prevents
them from being created. So this design makes adding operations cheap and adding
constructors expensive, the opposite of putting each operation inside the
expression classes.

## Known limitations

- **Recursion depth.** The visitors recurse like the supplied ones, so
  expressions nested deeper than Python's recursion limit raise `RecursionError`.
- **Very large integers.** `str()` of an integer with more than 4300 digits
  raises `ValueError` in Python 3.11 and later (the interpreter's default limit),
  so such a literal cannot be pretty-printed unless the limit is raised.
- **Sharing.** Results may share unchanged subtrees with the input, and the
  replacement object itself is inserted at every replaced occurrence. Inputs
  are never modified, but modifying a result afterwards (the expression classes
  are mutable dataclasses) can also change an input.
- **Conservative renaming.** A binder is renamed whenever the target is free in
  its body and the binder name is free in the replacement, even if every
  replaced occurrence sits under an inner binder of the same name. The result is
  still alpha-equivalent; there may be one renaming more than strictly needed.
- **No input validation.** Variable names are assumed to be identifiers and
  operator names are printed as given.
- **Tests.** The tests use the supplied evaluator only as an independent check
  of substitution (the substitution lemma on random terms); the visitors never
  call it.
