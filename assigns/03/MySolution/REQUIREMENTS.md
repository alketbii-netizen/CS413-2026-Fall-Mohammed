# Requirements Specification: LAMBDA Web-Based Testing Environment

## 1. Purpose

This document specifies the requirements for a web-based environment in which
students and the instructor can write LAMBDA programs, compile and/or run
them against the LAMBDA compiler, inspect the results (including, when
available, compiler-internal information such as an abstract syntax tree or
generated code), and save programs as named, repeatable tests. The purpose
of the first version is to replace ad hoc, direct use of the language tools
with a more convenient, browser-based workflow for trying programs and
regression-testing the compiler, while keeping the scope small enough to
ship reliably.

This specification describes required *behavior*. It intentionally avoids
prescribing a UI framework, programming language, storage engine, or
internal compiler-interface protocol, except where the brief itself commits
to a specific choice.

## 2. Stakeholders

| Stakeholder | Interest |
|---|---|
| **Course instructor** | Commissions the system; uses it live in lectures to run and modify example programs; wants an approachable tool for students new to the compiler; is the primary source of requirements in this document. |
| **Students writing LAMBDA programs** | Use the environment to write, run, and understand the output of their own programs; may have little or no prior experience with the compiler. |
| **Students working on the compiler** | Use the environment to check whether their compiler changes still produce correct results, via saved test collections. |
| **Compiler team** (may overlap with student developers) | Provides and evolves the compiler interface the environment depends on; the brief notes this interface is still being designed. |

## 3. Scope

### 3.1 In scope for the first version

- A single-user, browser-based page for editing one LAMBDA program at a
  time, with example programs to start from (REQ-01–REQ-04).
- Compiling and/or running a program and displaying results, including
  compile errors, runtime errors, and (when available) AST/generated-code
  inspection (REQ-05–REQ-10).
- Local persistence of the student's or instructor's work across page
  reloads and sessions, on the same machine (REQ-11–REQ-13).
- A named collection of tests, each with a program and an expected outcome
  (expected value or expected rejection), runnable as a batch with a
  pass/fail summary (REQ-14–REQ-18).
- Cancelling a long-running or non-terminating program (REQ-09).
- Running against either the real compiler or a documented set of sample
  ("mock") compiler responses, so that interface work can proceed before the
  compiler is ready (REQ-19).
- Keyboard operability and color-independent status messaging for the core
  workflow (REQ-20, REQ-21).

### 3.2 Explicitly out of scope for the first version

- Public hosting, user accounts, authentication, or any multi-user server
  deployment; the brief asks only for something that runs locally on a
  student's or instructor's own machine.
- Real-time collaborative editing of the same program by multiple people.
- Sharing a test collection with the whole class (the brief states this is
  desirable but acceptable to omit initially).
- Any specification of the LAMBDA compiler's own behavior, language design,
  or implementation — the compiler is a **separate, external project** with
  its own interface, referenced here only as a dependency.
- Any specific choice of UI toolkit, editor component, storage technology,
  or transport protocol between the environment and the compiler, unless
  the brief requires it.

### 3.3 System boundary: testing environment vs. compiler

The **testing environment** (the subject of this specification) is the
browser-based application that a student or instructor interacts with
directly: the editor, the run/compile controls, the results display, and
the test-collection manager. The **compiler** is an external, independently
developed component (currently a course interpreter working with
Python-constructed ASTs, per the brief) that the environment calls through
an interface boundary. The environment must be able to operate against
either a real compiler implementation or a documented substitute for
demonstration purposes (see REQ-19), without requiring that the environment
itself be rebuilt when the real compiler becomes available.

## 4. Functional Requirements

Each requirement has a unique ID, a priority (**Must**, **Should**, or
**Could**, using a MoSCoW-style scale), and, where the brief's wording is
open-ended, a note on how it was interpreted.

| ID | Requirement | Priority |
|---|---|---|
| REQ-01 | The system shall let the user open the environment to a blank or example program without any prior setup beyond following the provided run instructions. | Must |
| REQ-02 | The system shall provide a set of built-in example programs (at minimum, one arithmetic/recursive example such as factorial) that the user can load into the editor with a single action. | Must |
| REQ-03 | Loading an example program shall not overwrite or delete the original example; the user edits a working copy, and the original remains available to reload. | Must |
| REQ-04 | The system shall let the user type or paste a LAMBDA program into an editing area, and shall let the user load a program from a file on their own computer instead of retyping it. | Must |
| REQ-05 | The system shall let the user request compilation of the current program without running it, and shall report whether compilation succeeded or failed. | Must |
| REQ-06 | The system shall let the user run the current program and display the resulting value (or the fact that it produced no value, if applicable) once execution completes. | Must |
| REQ-07 | On a compilation error, the system shall display an explanation of the error and, when the compiler reports a source location for the error, shall visually indicate that location in the user's source text. | Must |
| REQ-08 | The system shall visually and textually distinguish a compilation failure from a runtime failure; the two shall never be presented as the same kind of outcome. | Must |
| REQ-09 | While a program is running, the system shall allow the user to stop it and return the editor to a usable state, without requiring the user to close or reload the page. | Must |
| REQ-10 | When the compiler provides supplementary information about a program (for example, an abstract syntax tree or generated code), the system shall let the user optionally view it, without displaying it by default during an ordinary run. | Should |
| REQ-11 | The system shall preserve the user's current program text across a page reload, without requiring an explicit save action. | Must |
| REQ-12 | The system shall let the user explicitly save the current program under a name and reload it in a later session on the same machine. | Must |
| REQ-13 | If the environment cannot reach the compiler (for example, the compiler process is not running), the system shall report this as an environment problem, distinct from a compilation or runtime error in the user's program, and shall preserve the user's current program text so no work is lost. | Must |
| REQ-14 | The system shall let the user create a named test consisting of a program and an expected outcome, where the expected outcome is either a specific value (e.g., an integer or Boolean) or an expectation that the compiler rejects the program. | Must |
| REQ-15 | The system shall let the user group named tests into a persisted collection that survives page reloads and later sessions, in the same way as saved programs (REQ-11–REQ-12). | Must |
| REQ-16 | The system shall let the user run an entire test collection in one action and shall report, for each test, whether its actual outcome matched its expected outcome. | Must |
| REQ-17 | The system shall present a summary of a test-collection run (counts of passed/failed/errored tests) together with enough per-test detail (e.g., actual vs. expected outcome, and any error message) to investigate a failing test without re-running it individually. | Must |
| REQ-18 | A test that fails or whose execution raises an unexpected error shall not prevent the remaining tests in the collection from running and being reported. | Must |
| REQ-19 | The system shall support operating against a documented set of sample/mock compiler responses in place of a real compiler connection, and any output produced this way shall be clearly and consistently labeled as sample/demonstration output, not as an actual compilation or execution result. | Must |
| REQ-20 | The system shall allow the primary tasks — loading an example, editing a program, compiling, running, stopping a run, and managing tests — to be performed using only the keyboard. | Should |
| REQ-21 | The system shall communicate status (e.g., success, compile error, runtime error, environment error, running/stopped) through means that do not rely on color alone (e.g., icons, text labels, or both). | Must |
| REQ-22 | If the user changes the program in the editor while a previous run of an earlier version is still in progress, the system shall indicate, once that earlier run completes, which version of the program produced the displayed result. | Should |

*(22 functional requirements: the brief's suggested range is 12–20; the
extra items were kept because each addresses a distinct behavior the
instructor explicitly raised — see the traceability table in Section 7 —
rather than being split out to inflate the count. REQ-01–REQ-22 could be
consolidated to roughly 16–18 by merging closely related pairs, e.g.
REQ-11/REQ-12, if a stricter count is required; both are kept separate here
because "preserved automatically" and "saved explicitly under a name" are
functionally distinct and independently testable.)*

## 5. Quality Requirements

| ID | Requirement | How satisfaction is assessed | Priority |
|---|---|---|---|
| QR-01 | **Responsiveness under load.** The editor and its controls (typing, navigating, invoking a new action) shall remain usable while a compile or run request is in progress, even if the compiler itself takes noticeably longer to respond. | Verified by exercising editor input (typing, scrolling, clicking another control) during an in-progress run and confirming the UI accepts and reflects that input without freezing, per REQ-09/REQ-22 scenarios. | Must |
| QR-02 | **Error clarity.** An error message shown to the user shall include, at minimum, what kind of failure occurred (compile, runtime, or environment) and any location or cause information the compiler supplies, in language a student new to the compiler can act on. | Verified by acceptance scenarios AC-02 and AC-03 (Section 6), which check that error type and location (when available) are both present and distinguishable. | Must |
| QR-02 replaces the brief's own wording ("easy to understand", "useful explanation") — those terms are avoided as stated because they are not independently checkable; QR-02's assessment method is the proposed operationalization. | | | |
| QR-03 | **Persistence reliability.** No user-initiated save of a program or test (REQ-12, REQ-15) shall be silently lost; if a save cannot be completed, the system shall report the failure rather than proceeding as if it succeeded. | Verified by attempting a save under a simulated storage failure and confirming an explicit failure notice is shown, and by confirming a normal save is retrievable after a reload. | Must |
| QR-04 | **Recoverability from environment failure.** After the compiler becomes unreachable (REQ-13) and is later restored, the user shall be able to resume compiling/running without having lost the program they were editing or needing to restart the environment. | Verified by acceptance scenario AC-04 (Section 6). | Must |
| QR-05 | **Setup reproducibility.** A person other than the original developer shall be able to follow the provided setup instructions and get the environment running locally without additional undocumented steps. | Verified by having a second person (not the developer) follow the written setup instructions on a clean machine/environment and successfully load the environment. | Should |

This section deliberately avoids "fast" and "easy to use" as unqualified
claims, per the assignment's instruction; where the brief used such
language, the requirement above either ties it to an observable check
(QR-01, QR-02) or flags a proposed assessment method as a **proposal**
subject to the instructor's confirmation (all rows in the "How satisfaction
is assessed" column that are not directly quoting the brief).

## 6. External Interfaces and Dependencies

- **Compiler interface (critical, evolving dependency).** The environment
  depends on a compiler component described in the brief as "the current
  course interpreter," which works with abstract syntax trees constructed in
  Python; the notation for LAMBDA source programs is explicitly stated to be
  still under discussion. The exact call/response protocol between the
  environment and the compiler is **not specified by the brief** and is
  recorded as an open question (CQ-01, CQ-02 in Section 8). Per REQ-19, the
  environment must be buildable and demonstrable against a documented
  substitute for this interface before it is finalized.
- **Local file system access.** REQ-04 (loading a program from a file) and
  REQ-11/REQ-12/REQ-15 (persistence across sessions) imply the environment
  reads from and writes to storage on the user's own machine — browser
  storage, local files, or an equivalent local mechanism. No specific
  mechanism is mandated here; see CQ-04.
- **Browser environment.** The brief specifies only "a browser students
  normally use" — no specific browser or version is named. This is recorded
  as an open assumption (A-04, Section 8).
- **No network services, accounts, or external identity providers** are
  required or in scope, per Section 3.2.

## 7. Priorities

Priorities are assigned per-requirement in Sections 4 and 5 using a
MoSCoW-style scale (Must / Should / Could). At the feature-group level, the
instructor's own closing statement in the brief — "reliable editing,
understandable results, and repeatable tests are more important... than
sophisticated visual effects" — is treated as the standing priority order
for this project:

1. **Must-have core:** reliable single-program editing, compiling, and
   running, with clear, correctly-categorized error/result reporting
   (REQ-01–REQ-09, REQ-11–REQ-13, REQ-21).
2. **Must-have testing:** the named-test collection and its repeatable,
   fault-isolated batch run (REQ-14–REQ-18).
3. **Must-have de-risking:** the mock-compiler mode that decouples
   environment development from compiler readiness (REQ-19).
4. **Should-have polish:** AST/generated-code inspection, full keyboard
   operability, and version-tracking of in-flight runs (REQ-10, REQ-20,
   REQ-22), plus setup reproducibility (QR-05).
5. **Could-have / explicitly deferred:** class-wide sharing of a test
   collection (Section 3.2), multi-user editing, and any visual polish
   beyond REQ-21's accessibility floor.

## 8. Clarification Questions, Assumptions, and Unresolved Issues

The brief was written informally and leaves several points unresolved. The
questions below are ones a requirements author would need answered before
implementation; none of them have a recorded stakeholder answer at the time
of writing, so each is paired with the assumption used to proceed in this
document, or is left explicitly unresolved.

| ID | Clarification question | Why it matters | Assumption used here (if any) / status |
|---|---|---|---|
| CQ-01 | What is the exact call/response contract between the environment and the compiler (input format, e.g. source text vs. pre-built Python AST; output format for values, errors, and source locations)? | Directly determines REQ-05–REQ-08, REQ-10, and REQ-19's mock-mode design; without it, the interface boundary cannot be implemented, only stubbed. | **Unresolved.** The brief says the notation for source programs is "still being discussed," so this document specifies required *behavior* at the boundary (REQ-05–REQ-08) without assuming a protocol. |
| CQ-02 | Is the compiler expected to run as a separate local process/service the environment talks to, or be embedded/imported directly into the environment's own code? | Affects REQ-13 (what "cannot reach the compiler" means concretely) and the environment's failure-handling design. | **Assumption:** treated as a separate reachable component, since the brief explicitly describes it as something the environment might "reach" or fail to reach. |
| CQ-03 | What exactly should count as a "long-running" program that the user may want to stop (REQ-09) — is there a specific timeout, or is cancellation purely user-initiated at any time? | Determines whether REQ-09 needs an automatic timeout requirement in addition to manual cancellation. | **Assumption:** cancellation is user-initiated only, at any time during a run; no automatic timeout is assumed, since the brief only says a program "might never finish" and describes wanting "a way to stop it," not an automatic cutoff. |
| CQ-04 | Where and how should saved programs and test collections persist (e.g., browser local storage, local files on disk, a local project directory)? Should saved data be portable between machines? | Affects REQ-11–REQ-12, REQ-15, and QR-03's failure-mode design, and whether "another session" means the same browser profile or literally any access to the same files. | **Unresolved**, recorded as an implementation decision to be made with the instructor; this document specifies only the observable persistence behavior, not the storage mechanism. |
| CQ-05 | For the AST/generated-code inspection feature (REQ-10), what level of detail is wanted, and is this needed in the first version or acceptable to defer? | Affects whether REQ-10 is Must or Should; the brief calls this "useful for teaching" but does not say it's required for a first release. | **Assumption:** classified as Should (useful but not blocking), consistent with the instructor's stated preference for a "useful small version" over comprehensive tooling. |
| CQ-06 | Should the "quick summary" of a test-collection run (REQ-17) have any specific required format (e.g., pass count only, or a full per-test table always visible)? | Affects the acceptance criteria for REQ-17 and how much detail is "enough" per the brief's own phrasing. | **Assumption:** a summary count plus on-demand per-test detail (not necessarily all shown at once) satisfies the brief's "quick summary... with enough detail to investigate." |
| CQ-07 | Is there a minimum or target set of example programs to ship (the brief mentions "factorial" as an example, and says "a few examples")? | Affects the acceptance criteria for REQ-02 (how many examples count as satisfying "a few"). | **Assumption:** at least one worked example (factorial, as named in the brief) is treated as the Must-have minimum for REQ-02; "a few" beyond that is a Should, left to implementation discretion. |
| CQ-08 | Does "keeping examples as tests" (Section on tests) require expected-output tests only, or should the system also support tests with no fixed expected output (e.g., "just don't crash")? | Affects the completeness of REQ-14's definition of a test's expected outcome. | **Assumption:** REQ-14 supports exactly the two outcome kinds the brief names (expected value, expected rejection); an open-ended "no crash" test type is out of scope unless the instructor asks for it. |

## 9. Acceptance Criteria

Each entry identifies the requirement being checked, the starting
condition, the action/input, and the observable expected result. AC-05 and
AC-06 are failure/exceptional scenarios, as required.

**AC-01 — Loading and running an example (REQ-02, REQ-06)**
- *Requirement:* REQ-02, REQ-06
- *Starting condition:* Environment is freshly opened; editor is empty.
- *Action:* User selects the built-in factorial example, then requests a run with input `5`.
- *Expected result:* The editor shows the factorial program; after the run completes, the displayed result is `120`, with no error indication shown.

**AC-02 — Compilation error with location (REQ-05, REQ-07, REQ-08, QR-02)**
- *Requirement:* REQ-05, REQ-07, REQ-08, QR-02
- *Starting condition:* Editor contains a LAMBDA program with a deliberate syntax error at a known line.
- *Action:* User requests compilation (not run).
- *Expected result:* The system reports a compilation failure (labeled distinctly from a runtime failure), displays an explanation of the error, and — since the compiler reports a location — highlights that location in the source editor.

**AC-03 — Runtime error is not mistaken for a compile error (REQ-08)**
- *Requirement:* REQ-08
- *Starting condition:* Editor contains a program that compiles successfully but raises an error during execution (e.g., division by zero).
- *Action:* User requests a run.
- *Expected result:* The program is reported as having compiled successfully, and a separate runtime-failure indication is shown once execution fails; the two states are visually/textually distinguishable from each other and from AC-02's compile failure.

**AC-04 — Environment failure does not look like a program error, and work is preserved (REQ-13, QR-04)**
- *Requirement:* REQ-13, QR-04
- *Starting condition:* User has an unsaved, partially edited program in the editor; the compiler connection is then made unavailable (e.g., the compiler process is stopped).
- *Action:* User requests a run.
- *Expected result:* The system reports an environment-level failure (distinct from a compile or runtime error), the user's unsaved program text remains present and editable, and once the compiler connection is restored, the user can successfully run the same program without having retyped anything.

**AC-05 — Stopping a non-terminating program (failure/exceptional scenario) (REQ-09, QR-01)**
- *Requirement:* REQ-09, QR-01
- *Starting condition:* Editor contains a program with unbounded recursion (never terminates).
- *Action:* User starts a run, waits briefly, then invokes the stop/cancel control.
- *Expected result:* The run is terminated, the editor and its controls remain responsive throughout (the page did not freeze while the run was in progress), and the user can immediately start a new run or edit the program.

**AC-06 — One failing test does not block the rest of a collection (failure/exceptional scenario) (REQ-16, REQ-17, REQ-18)**
- *Requirement:* REQ-16, REQ-17, REQ-18
- *Starting condition:* A saved test collection contains five tests: three expected to pass, one expected to fail its assertion (wrong value), and one whose program causes an unhandled error during execution.
- *Action:* User runs the entire collection in one action.
- *Expected result:* All five tests are attempted and reported; the summary shows 3 passed / 1 failed / 1 errored (or equivalent categorization); per-test detail is available for the failed and errored tests showing their actual vs. expected outcome; the failing or erroring test does not prevent the other four from being run and reported.

## 10. Traceability Table

| Requirement | Source in brief / stakeholder answer / assumption |
|---|---|
| REQ-01 | Brief, "It should be easy to get started, including for someone who has not used the compiler before." |
| REQ-02 | Brief, "Having a few examples to start from would help... I might select a factorial example." |
| REQ-03 | Brief, "Students should be able to modify an example without losing access to the original." |
| REQ-04 | Brief, "Students may already have programs saved in files, and they should not have to retype them." |
| REQ-05 | Brief, "Sometimes I only want to check whether a program compiles." |
| REQ-06 | Brief, "At other times, I want to run it and see the answer." |
| REQ-07 | Brief, "When the compiler reports where the problem occurred, the environment should help the student find that place in the source." |
| REQ-08 | Brief, "A compilation error and a failure while running the program should not look like the same thing." |
| REQ-09 | Brief, "Some examples may run for a long time... There should be a way to stop it and move on." |
| REQ-10 | Brief, "it would also be useful to inspect information the compiler produces, such as an abstract syntax tree or generated code... I do not want all of that detail to get in the way." |
| REQ-11 | Brief, "I would be frustrated if refreshing the page meant losing the examples I had prepared." |
| REQ-12 | Brief, "Students will also want to come back to their work in another session," combined with REQ-03's "keep a program they have written." |
| REQ-13 | Brief, "If it cannot reach the compiler, I do not want students to think their program is wrong. They should be able to keep their work and try again." |
| REQ-14 | Brief, "Each test would contain a program and some record of what should happen... Some tests would expect an answer... Others would intentionally contain an error." |
| REQ-15 | Brief, "students to keep a collection of named tests," plus REQ-11/12's persistence expectation extended by assumption (CQ-04 unresolved on mechanism). |
| REQ-16 | Brief, "a student could run the collection again to check whether anything has broken." |
| REQ-17 | Brief, "I would like a quick summary of which tests worked as expected, with enough detail to investigate the ones that did not." |
| REQ-18 | Brief, "One troublesome test should not make the rest of the collection useless." |
| REQ-19 | Brief, "I would like work on the interface to proceed even before the compiler is ready. Using sample compiler responses... would be acceptable, as long as nobody mistakes them for actual compilation results." |
| REQ-20 | Brief, "Students should be able to perform the main tasks with a keyboard." |
| REQ-21 | Brief, "messages should make sense without depending only on colors." |
| REQ-22 | Brief, "If I change a program while an earlier run is still working, I need to know which version produced the result I am seeing." |
| QR-01 | Brief, "The environment should respond promptly to ordinary actions, even when the compiler takes longer to finish." |
| QR-02 | Brief, "The result should be easy to understand... I want the student to see a useful explanation," reworded per assignment instructions to be assessable (assumption on assessment method). |
| QR-03 | Assumption, derived from REQ-12/REQ-15's persistence requirement — the brief does not explicitly discuss save failures. |
| QR-04 | Brief, "They should be able to keep their work and try again when the problem is resolved" (same passage as REQ-13). |
| QR-05 | Brief, "the setup should be straightforward enough that another person can follow the instructions and get it running." |
| Scope: local-only, no accounts | Brief, "running locally on a student's or instructor's computer is enough. I am not asking for a public website, user accounts, or several people editing the same program together." |
| Scope: compiler is separate | Brief, "Developing the compiler itself is a separate project." |

## 11. Review Notes

The following issues were found on review of the first draft of this
specification and addressed as noted:

1. **Ambiguity in "understandable results."** The initial draft carried the
   brief's own language ("easy to understand," "useful explanation")
   directly into a requirement, which the assignment instructions flag as
   unverifiable. **Fix:** reworded as QR-02 with an explicit, checkable
   assessment method (message must name the failure category and include
   location info when available), and the reworded assessment method is
   labeled as a proposal rather than attributed to the stakeholder.
2. **Unclear persistence mechanism conflated with persistence behavior.**
   An early draft of REQ-11/REQ-12 implicitly assumed browser local storage
   without saying so, which would have quietly narrowed the design space
   (e.g., ruling out saving to local files) beyond what the brief supports.
   **Fix:** the requirements now describe only observable persistence
   behavior, and the storage mechanism is moved to an explicit open question
   (CQ-04) rather than a silent assumption.
3. **Missing distinction between environment failure and program failure.**
   The first pass covered compile vs. runtime error distinctions (REQ-08)
   but did not separately address the brief's paragraph about the
   environment itself failing to reach the compiler. **Fix:** added REQ-13
   and QR-04 as their own requirements, with a dedicated acceptance scenario
   (AC-04), since conflating "my program is wrong" with "the environment is
   broken" is exactly the confusion the instructor said they wanted to
   avoid.
4. **Requirement count risked inflation.** To reach the suggested 12–20
   range, an early draft split "save a program" and "reload a program" into
   four separate requirements. **Fix:** consolidated to the two requirements
   (REQ-11 automatic/session persistence, REQ-12 explicit named save) that
   correspond to genuinely distinct, separately testable behaviors the
   brief describes, rather than splitting for the sake of a count, per the
   assignment's explicit instruction not to do so.
