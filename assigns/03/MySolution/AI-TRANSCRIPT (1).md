# AI-TRANSCRIPT

**AI system used:** Claude (Anthropic), used interactively through the
Claude chat interface. No code was written for this assignment — the
work is a requirements specification document, so this transcript
describes the analysis and drafting process instead of a code-review
process.

## Context

`Assign03.md` asked for a requirements specification to be produced from
an informal stakeholder brief (`LAMBDA-UI-informal-requirements`)
describing a wanted web-based environment for editing, compiling, running,
and testing LAMBDA programs. The brief is written the way a real
stakeholder would write one: in prose, from the instructor's point of
view, mixing genuine requirements with wishes, unstated assumptions, and
open questions, and with no requirement IDs, no explicit prioritization,
and no acceptance criteria of its own. The assignment's actual task is to
turn that prose into a structured specification, not to design or build
the LAMBDA environment itself ("You are not required to implement the UI,
compiler, or any other software").

## Process

1. **Read the brief line by line and classified each sentence.** For each
   sentence in the stakeholder brief, asked: is this (a) a testable
   functional requirement, (b) a quality/non-functional requirement, (c) a
   scope boundary (in/out), (d) an assumption or open question the brief
   raises but does not answer, or (e) just color/motivation with no
   requirement content. This pass produced the raw material behind
   Sections 4 and 5 of `REQUIREMENTS.md`.

2. **Identified stakeholders and the system boundary first**, before
   writing individual requirements, since several requirements (e.g. the
   compiler-unreachable case, the mock-compiler mode) only make sense once
   the environment/compiler boundary is drawn explicitly. The brief calls
   the compiler "a separate project," which was taken at face value: the
   specification describes required behavior at the boundary (e.g., "the
   system shall report a failure to reach the compiler") without inventing
   a protocol the brief doesn't specify.

3. **Drafted functional requirements with unique IDs**, checking each one
   against a testability bar: could a QA person, given only the requirement
   text, write a pass/fail test for it without asking a follow-up question?
   Requirements that failed this bar on the first pass were reworded or
   split. Example: the brief's sentence about keeping work when the
   compiler is unreachable was originally folded into the general
   error-handling requirement; it was pulled out into its own requirement
   (now REQ-13) because "compiler is broken" and "student's program is
   broken" are different failure categories that the instructor explicitly
   said should never be presented the same way, and lumping them together
   would have made both harder to test independently.

4. **Deliberately avoided restating the brief's own unmeasurable language**
   ("easy to understand," "fast," "useful") as if it were already a
   requirement. Where the assignment instructions call for measurable
   quality requirements, each such phrase was either tied to an explicit,
   checkable condition (e.g., QR-02 requires an error message to name its
   failure category and include location info when available, rather than
   just being "understandable") or flagged as an assumed interpretation
   subject to the instructor's confirmation, rather than presented as
   something the brief itself pinned down.

5. **Extracted clarification questions from genuine gaps**, not invented
   ones. Went back through the brief looking specifically for places where
   (a) a decision is clearly needed to implement a requirement and (b) the
   brief does not supply enough information to make that decision — e.g.,
   the exact environment/compiler call protocol, and where saved
   programs/tests should live. Each such gap became one clarification
   question (CQ-01 through CQ-08) paired with either an explicit assumption
   used to keep the rest of the document self-consistent, or a note that
   the question is left genuinely unresolved.

6. **Wrote acceptance criteria as concrete scenarios**, including two
   failure/exceptional scenarios as required (AC-05: cancelling a
   non-terminating program; AC-06: one failing test not blocking the rest
   of a test-collection run), each with a starting condition, an action,
   and an observable expected result — deliberately avoiding vague
   acceptance language like "works correctly."

7. **Built the traceability table last**, after the requirements were
   stable, by going back through the brief a second time and matching each
   requirement to the specific sentence(s) that motivated it. This pass
   caught one requirement (an early draft's "the system should look
   modern") that had no traceable source in the brief at all — it was
   something I had added on my own initiative rather than derived from the
   stakeholder's actual words, and it was removed, since the instructor's
   own closing note in the brief explicitly deprioritizes visual polish
   ("reliable editing, understandable results, and repeatable tests are
   more important... than sophisticated visual effects").

## Self-review: issues found and fixed

This mirrors the "review AI-generated output with confidence" expectation
from earlier assignments, applied here to a specification instead of code.
Three issues were found on review of the first draft (recorded in full in
`REQUIREMENTS.md` Section 11, "Review Notes") and fixed before finalizing:

1. **Unmeasurable quality language copied verbatim from the brief**
   ("easy to understand") was initially left as the requirement text
   itself. Fixed by rewriting it as a requirement with an explicit
   assessment method (QR-02) and labeling that assessment method as a
   proposal, not something the stakeholder specified.
2. **A storage mechanism (browser local storage) was silently assumed**
   for the persistence requirements, which would have narrowed the design
   more than the brief supports. Fixed by describing only the required
   *behavior* of persistence and moving the mechanism choice to an
   explicit open question (CQ-04).
3. **The distinction between "the environment is broken" and "the
   student's program is broken"** was not given its own requirement in the
   first pass — it was folded into the general compile/runtime error
   requirement. Fixed by adding a dedicated requirement (REQ-13), a
   matching quality requirement (QR-04), and a dedicated acceptance
   scenario (AC-04), since this was one of the more specific and
   emphatic points in the instructor's brief and deserved to be
   independently testable rather than implied.

A fourth check — requirement-count inflation — was also caught and fixed:
an early draft split "auto-preserve on reload" and "explicit named save"
into four separate requirements to pad toward the suggested count; on
review this was judged to be splitting for the sake of a number rather
than because the behaviors were truly distinct, so it was collapsed back
to two requirements that are each independently testable and each trace to
a distinct sentence in the brief.

## What I did NOT trust the AI to do unchecked

Every requirement in `REQUIREMENTS.md` was checked against the traceability
table before finalizing — i.e., I did not accept a requirement's presence
in the document as evidence that it belonged there; I required it to trace
back to an actual sentence in the stakeholder brief or to be explicitly
labeled as my own assumption. This caught the one untraceable "modern
look" requirement described above. I also independently re-read the
assignment's evaluation criteria in `Assign03.md` against the finished
document section-by-section to confirm every required section (clarifying
questions, functional/quality requirements, external interfaces,
priorities/assumptions, acceptance criteria with failure scenarios,
traceability, and review notes) was actually present, rather than trusting
that asking for all of them in one pass would produce all of them.
