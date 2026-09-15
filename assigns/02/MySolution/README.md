# AST Expression Evaluator — AI-Assisted

## Note on the assignment brief

`Assign02.md` in the class repo (as of when this was done) contained
only the title, due date, and a one-sentence Objective — no Tasks or
deliverables list. Per the instructor's own note in the class repo
("Assign02 is out... the real point here is to make sure that you
understand the involved concepts and are able to review AI-generated
code with confidence"), the concrete task below was chosen as a
reasonable, self-contained way to satisfy the stated Objective
("gain practical experience with abstract syntax trees (ASTs)").
If this doesn't match what was intended, please let me know and I'll
adjust.

## Contents

- `expr_ast.py` — tokenizer, recursive-descent parser producing an
  explicit AST (`Num` / `BinOp` / `UnaryOp` node types), an AST
  pretty-printer, and an AST-walking evaluator for arithmetic
  expressions (`+ - * /`, parentheses, unary +/-, standard precedence).
- `test_expr_ast.py` — automated test cases (normal, boundary, custom).
- `AI-TRANSCRIPT.md` — record of the AI-assisted development process,
  including a real associativity bug that was found and fixed.

## How to run

```
python3 expr_ast.py
python3 test_expr_ast.py
```

## AI Reflection

I used Claude to write a small arithmetic-expression parser that
builds an explicit Abstract Syntax Tree and evaluates it — the goal
being to actually get hands-on with what an AST is and how one gets
built and walked, since the assignment's brief was very short on
detail beyond that goal. The AI did well at producing a clean,
standard grammar (expr/term/factor) and clear AST node types using
Python dataclasses, and at adding a pretty-printer that made the tree
structure directly visible rather than just the final numeric answer.

The weakness showed up when I actually ran the program on a chain of
same-precedence operators. `10 - 3 - 2` returned `9` instead of the
correct `5`. Printing the AST made the cause obvious: the parser had
recursed on the right-hand side of each operator, which builds a
right-associative tree even for operators like `-` and `/` that are
mathematically left-associative. `10 - (3 - 2)` and `(10 - 3) - 2` are
different expressions with different values, and only the second is
the standard reading of `10 - 3 - 2`. This is a well-known
recursive-descent parsing pitfall, and it's the kind of bug that's
easy to miss if you only test single-operator or two-operand
expressions — it only shows up once you chain three or more terms of
the same precedence.

To verify the fix (switching from recursion to an explicit loop that
folds terms onto a growing left-hand tree), I didn't just check that
the number came out right — I also wrote a test that inspects the
actual shape of the resulting AST (which node is on the left, which
operator is at the root), since a coincidentally-correct number
doesn't prove the tree itself is right.

I would not have trusted the first version without running it and
looking at the tree it produced, not just the final answer — the bug
was invisible from the code alone unless you traced through what the
recursion actually does for a three-term expression, and it was
invisible from a "does it run without crashing" check. Using AI here
meant the grammar and node types came together quickly, but verifying
correctness meant actually exercising the AST structure itself, which
is exactly the "understand the involved concepts" the assignment's
note asked for — the value wasn't in trusting the AI's first answer,
it was in knowing what to check.
