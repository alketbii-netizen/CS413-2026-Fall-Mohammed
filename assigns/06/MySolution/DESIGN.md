# Design: Compiling Extended LAMBDA into Pure Lambda-Calculus

## 1. Architecture

```text
source AST ──compile_expr (CompileVisitor)──▶ pure Term ──evaluate(term, budget)──▶ Lam value
   │                                                                                  │
   └──evaluate(source)──▶ source value (expected answer)      observe(value, kind)──▶ int / bool / tuple
```

Five modules with one-way dependencies: `target` (syntax and substitution) ←
`church` (encodings) ← `compiler`; `target` ← `evaluator` ← `observe`. The
compiler never imports the evaluator, and the evaluator never imports the
compiler, so compilation cannot execute code and execution cannot compile.

## 2. Representations

```text
I        = lam w. w
TRUE     = lam t. lam f. t                 FALSE = lam t. lam f. f
NUM(n)   = lam s. lam z. s (... (s z))     PAIR  = lam a. lam b. lam p. p a b
FST      = lam p. p (lam a. lam b. a)      SND   = lam p. p (lam a. lam b. b)
NOT      = lam b. lam t. lam f. b f t
SUCC     = lam n. lam s. lam z. s (n s z)
ADD      = lam m. lam n. lam s. lam z. m s (n s z)
MUL      = lam m. lam n. lam s. m (n s)
ISZERO   = lam n. n (lam x. FALSE) TRUE
PRED     = lam n. FST (n (lam q. PAIR (SND q) (SUCC (SND q))) (PAIR NUM(0) NUM(0)))
SUB      = lam m. lam n. n PRED m
LEQ      = lam m. lam n. ISZERO (SUB m n)
LT       = lam m. lam n. ISZERO (SUB (SUCC m) n)
GEQ      = lam m. lam n. LEQ n m           GT  = lam m. lam n. LT n m
ANDS     = lam p. lam q. p q p             (strict; operands already values)
EQ       = lam m. lam n. ANDS (LEQ m n) (LEQ n m)
NEQ      = lam m. lam n. NOT (EQ m n)
Z        = lam g. (lam x. g (lam v. x x v)) (lam x. g (lam v. x x v))
```

All are closed; the abbreviations are Python builder functions whose
expansions are placed in the output, so output contains only `Var`, `Lam`,
`App` (checked by `is_pure` in the tests).

## 3. Translation rules

```text
C[n]                    = NUM(n)                      (n >= 0, else CompileError)
C[true] / C[false]      = TRUE / FALSE
C[x]                    = x
C[lam x. e]             = lam x. C[e]
C[e1 e2]                = C[e1] C[e2]
C[let x = e1 in e2]     = (lam x. C[e2]) C[e1]
C[if c then t else f]   = (C[c] (lam u. C[t]) (lam v. C[f])) I
C[e1 and e2]            = (C[e1] (lam u. C[e2]) (lam v. FALSE)) I
C[e1 or e2]             = (C[e1] (lam u. TRUE) (lam v. C[e2])) I
C[not e]                = NOT C[e]
C[e1 + e2]              = ADD C[e1] C[e2]
C[e1 - e2]              = SUB C[e1] C[e2]
C[e1 * e2]              = MUL C[e1] C[e2]
C[e1 < e2]              = LT  C[e1] C[e2]       C[e1 <= e2] = LEQ C[e1] C[e2]
C[e1 > e2]              = GT  C[e1] C[e2]       C[e1 >= e2] = GEQ C[e1] C[e2]
C[e1 == e2]             = EQ  C[e1] C[e2]       C[e1 != e2] = NEQ C[e1] C[e2]
C[pair e1 e2]           = PAIR C[e1] C[e2]
C[fst e] / C[snd e]     = FST C[e] / SND C[e]
C[fix f(x). e]          = Z (lam f. lam x. C[e])
any other op1/op2       = CompileError naming the operator
```

`u` and `v` are thunk parameters chosen by the naming policy below.

## 4. Predecessor

Church numerals can only iterate forward, so `PRED` iterates a shift on pairs.
Starting from `(0, 0)`, `SHIFT (a, b) = (b, b + 1)`. After one shift we have
`(0, 1)`, after two `(1, 2)`, and after `n ≥ 1` shifts `(n-1, n)`; with
`n = 0` no shift happens and the pair stays `(0, 0)`. Taking `FST` gives
`n - 1` for positive `n` and `0` for `0`, which is exactly the truncated
predecessor the language requires. Truncated subtraction `m - n` applies
`PRED` to `m` `n` times, so `2 - 5 = 0` falls out naturally. Under
call-by-value every intermediate pair is a value, so predecessor costs `O(n)`
beta steps and subtraction `O(m·n)`. I chose this over Church's original
`lam n. lam f. lam x. n (lam g. lam h. h (g f)) (lam u. x) (lam u. u)`
because the pair version is easier to explain and test.

## 5. Naming policy

The only binders the compiler places around translated code are thunk
parameters. For a thunk whose body is the translated term `T`, the parameter
is the first of `_k_1, _k_2, ...` that does not occur anywhere in `T` —
free, bound or as a binder. The choice is deterministic (same input, same
output) and the binder is unused in its body, so it can neither capture a
source variable nor change `FV`. Library combinators use fixed names such as
`s`, `z`, `t`, `f`, but they are closed and never wrap translated code; source
variables reach them only as arguments, through substitution, which is
capture-avoiding. So no source name is reserved: tests compile programs whose
variables are called `s`, `z`, `t`, `f`, `x`, `w`, `g`, `v`, `p`, `_k_1`, `tail`,
and `c`. Substitution renames a binder `y` to the first `y_i` outside
`names(body) ∪ FV(v) ∪ {x}` (adapted from Assignment 5).

Because each rule either reuses the source binder (`lam`, `let`, `fix`),
adds a closed combinator, or adds an unused fresh binder, induction on the
source gives `FV(C[e]) = FV(e)`, with `let` binding only in the body and the
inner `lam x` of `fix` shadowing `lam f` when `f = x`. The tests check this
on open expressions.

## 6. Evaluation strategy

`evaluator.evaluate` is the single evaluator. For a target term it runs weak,
left-to-right call-by-value: a `Lam` is a value (zero steps, even if its body
has redexes); for `App(m, n)` it evaluates `m` to `lam x. b`, then `n` to a value
`v`, then — if the budget allows one more step — contracts to `b[x := v]` and
continues. The step counter counts only beta-value contractions; renaming
inside substitution is free. A value reached on the last allowed step is
completed; needing a step with none left is "exhausted". Terms are immutable
dataclasses, so inputs are never mutated, and evaluation is deterministic.
Open target terms are rejected up front, because a stuck free variable is not
a value.

For a source AST the same evaluator dispatches through `D0ExpVisitor`: the
`var`, `lam`, `app` cases mirror the target cases (with closures in an
environment instead of substitution), and the source-only constructors use
the source rules: truncated subtraction, short-circuit `and`/`or`, boolean
`if`, left-to-right pair and operand evaluation, and `fix` closures whose
parameter is bound after the function name, so it shadows it. These source
results provide the expected answers in the demo and the tests.

## 7. Observation

Python never runs generated arithmetic. To read a natural, the observer
evaluates `v STEP BASE` with `STEP = lam tail. lam c. lam z. c tail` and
`BASE = lam c. lam z. z`. Call-by-value makes every `tail` a value, so the
result is a finite spine `lam c. lam z. c (… (lam c. lam z. z))`, which the
host counts, up to alpha-renaming, without reducing under lambdas. Booleans are
applied to two distinct closed markers `lam m1. lam m2. m1` and
`lam m1. lam m2. lam m3. m3`, and the result must be alpha-equal to one of
them. Anything else is `malformed`. Pairs are evaluated to a value, then `FST
p` and `SND p` are evaluated and observed with the expected kinds,
recursively. Observation has its own budget and step count. The kind must be
supplied, because `NUM(0)` and `FALSE` are the same term.

## 8. Correctness argument

**Claim.** For a closed, well-typed program `e` of the call-by-value source
language that evaluates to a natural, a boolean, or a finite pair of such
data, evaluating `C[e]` and observing the result with the corresponding kind
yields the same data, given sufficient execution and observation budgets.

**Values.** Each source value has a representation: `n` ↦ a term that behaves
like `NUM(n)` when applied, booleans ↦ `TRUE`/`FALSE`, pairs ↦ `PAIR` applied
to representations, and closures ↦ lambdas. Every source value translates to,
and evaluates to, a target value (a lambda), which matters for call-by-value.

**Application.** `C[e1 e2] = C[e1] C[e2]`. The target evaluates the function,
then the argument, then substitutes, just as the source evaluates `e1`, then
`e2`, then binds the parameter. Since translation commutes with substitution
of values (`C[e[x := v]] = C[e][x := C[v]]`, up to renaming, because the rules
are compositional and introduce only closed or fresh pieces), each source beta
step corresponds to a target beta-value step.

**Let.** `(lam x. C[e2]) C[e1]` evaluates `C[e1]` first because it is the
argument, then substitutes into the body — exactly let's order and scope:
`x` is not visible in `C[e1]`.

**Conditional.** `C[c]` evaluates to `TRUE` or `FALSE`, which selects one of
two *thunks*. Thunks are lambdas, hence already values, so neither branch is
evaluated when passed. Applying the selected thunk to `I` runs only that
branch. Without thunks, call-by-value would evaluate both branches as
arguments, so `if true then 1 else LOOP` would diverge and recursion through
`if` would never stop. `and`/`or` are conditionals with a constant branch, so
they short-circuit the same way.

**Recursion.** `Z F` with `F = lam f. lam x. C[e]` takes a few steps to reach
`F (lam v. W W v)` where `W W` unfolds to `Z F` again. The eta-expansion
`lam v. …` is a value, so the self-application is delayed until the
recursive function is actually called. Thus `Z F v ⇒ C[e][f := (lam v. W W v),
x := v]`, mirroring the source rule that binds `f` to the function and `x` to
the argument. The ordinary `Y` combinator would evaluate `x x` immediately
under call-by-value and loop forever before producing any value.

**Arithmetic and observation.** Each library combinator is checked
independently against Python on small inputs. The observers only apply pure
contexts and recognize final shapes, so the decoded value is a property of
the target term, not of host computation.

**Limits of testing.** The 53 tests and 15 demonstrations sample finitely many
programs. They can find bugs, but they cannot prove the claim for all
programs. A proof needs induction on source evaluation with a simulation
relation, which this argument only sketches. Budget exhaustion is likewise not
a proof of divergence.

## 9. Design tradeoffs

- **Substitution vs. environments in the target.** A substitution reducer
  follows the specified beta-value rule directly and makes step counts
  meaningful, but it copies terms. Caching `FV` per node and sharing subterms
  where the variable is not free keeps it fast enough (`fib 5` runs in about
  2,500 steps, which takes milliseconds).
- **Pair predecessor vs. Church's predecessor.** Simpler to explain and test; same
  linear cost under call-by-value.
- **Comparisons via subtraction.** `LEQ` and `LT` reuse `SUB` and `ISZERO`
  instead of new combinators. This costs `O(m·n)` steps but gives fewer
  definitions that could be wrong.
- **Fresh thunk names vs. constant names.** Picking `_k_i` per thunk costs a
  name-set lookup but keeps no source identifier reserved.
- **Closed-only execution.** Simpler, and documented. Compilation and
  substitution still fully support open terms.
- **No parser or type checker.** Out of scope, as the assignment allows; ill-typed
  programs may produce `malformed` observations.
