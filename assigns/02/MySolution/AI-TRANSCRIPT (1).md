# AI-TRANSCRIPT

**AI system used:** Claude (Anthropic), used interactively through the
Claude chat interface with a Linux code-execution sandbox available.

## Context / assumption made

At the time this was done, `Assign02.md` in the class repository
contained only a title, due date, and a single-sentence Objective
("gain practical experience with abstract syntax trees (ASTs), which
are used everywhere in compiler construction"), with no Tasks or
deliverables section. A course announcement from the instructor
("Assign02 is out... I am pretty sure that AI can finish it in a few
minutes. The real point here is to make sure that you understand the
involved concepts and are able to review AI-generated code with
confidence.") confirmed the assignment was intentionally posted this
way, and that the graded skill is reviewing AI-generated code rather
than following a long spec. Given only the Objective to go on, the
concrete task chosen was: build a small arithmetic-expression
tokenizer/parser that produces an explicit Abstract Syntax Tree,
an AST pretty-printer, and an AST-walking evaluator — a standard,
self-contained way to get hands-on AST experience.

## Initial prompt

Asked the AI to write a small Python program, `expr_ast.py`, that:
tokenizes an arithmetic expression (numbers, `+ - * /`, parentheses,
unary +/-), parses it into an explicit AST using dataclasses for node
types (`Num`, `BinOp`, `UnaryOp`), pretty-prints the tree structure,
and evaluates it — with standard operator precedence (`*`/`/` bind
tighter than `+`/`-`).

## Review process and bug found

The first version was generated as a straightforward recursive-descent
parser, with `parse_expr` and `parse_term` each written so that, after
matching an operator, they recursed on the right-hand side to consume
the rest of the expression (e.g. `right = self.parse_expr()` inside
`parse_expr` itself). This is a natural-looking way to write the
grammar rule `expr := term (('+' | '-') term)*` if you translate the
`*` (Kleene star) directly into recursion instead of a loop.

Before trusting it, the program was actually run on a handful of
inputs rather than just read. Printing the AST alongside the result
caught the problem immediately: for `10 - 3 - 2`, the AST was
`BinOp(-, Num(10), BinOp(-, Num(3), Num(2)))` — i.e. `10 - (3 - 2)`,
which evaluates to **9**. The correct, left-associative reading of
`10 - 3 - 2` is `(10 - 3) - 2 = 5`. The recursive formulation silently
builds a **right-associative** tree for operators (`-`, `/`) that are
mathematically left-associative, which gives the wrong answer any time
the same-precedence operator is chained three or more times in a row.
This is a classic recursive-descent parsing pitfall and a good
illustration of why reviewing an AST-producing program means checking
the *shape of the tree*, not just spot-checking a couple of outputs
that happen to look plausible.

**Fix (made manually after diagnosing the bug):** `parse_expr` and
`parse_term` were rewritten to use an explicit `while` loop that folds
each new right-hand term onto the growing left-hand tree
(`left = BinOp(op, left, right)`), which is the standard technique for
getting a left-associative tree out of a recursive-descent parser.

## Verification

After the fix, `10 - 3 - 2` produces the tree
`BinOp(-, BinOp(-, Num(10), Num(3)), Num(2))` and evaluates to `5.0`,
and a chained-division case (`100 / 10 / 5`) was added as a second
check of the same associativity property. Both, along with normal
precedence (`1 + 2 * 3 = 7`) and a parentheses/unary-minus case
(`-(2 + 3) * 4 = -20`), are covered in `test_expr_ast.py`, and one
test additionally inspects the AST node structure directly (not just
the final number) so that a lucky-but-wrong tree can't pass by
coincidence.

## Other review notes

- Operator precedence for `*`/`/` over `+`/`-` is handled by the
  grammar's two-level structure (`parse_expr` calls `parse_term` calls
  `parse_factor`), which was correct in the first draft and did not
  need changing.
- Unary plus/minus and parenthesized sub-expressions were correct in
  the first draft.
- No other functional bugs were found during testing.
