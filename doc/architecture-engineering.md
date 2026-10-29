# Python software design — engineering appendix

Python remains yap's application/domain core until further notice. Improve the
existing application through semantic values, cohesive modules and bounded
operations, while preserving authored sources and current portfolio behavior.
TypeScript may support browser presentation through those same operations.

This appendix supports the [product proposal](architecture-proposal.md) for
[issue #3](https://github.com/normenmueller/yap/issues/3). It distinguishes current
code, this draft's bounded checks and future contracts. It neither certifies the
whole codebase nor approves unfinished product behavior or portfolio migration.

<details>
<summary>Python architecture, type guarantees and verification boundaries</summary>

## Current baseline and remaining gaps

The application already selects one explicit instance per process and resolves
its resources from the application tree. The Python model feeds existing reports,
boards, maps and goal views. Activities and areas own YAML `wsp` maps; the
[authoring contract](authoring.md#local-workspaces) owns literal paths, named
navigation, explicit migration and publication exclusions.

The implementation still combines source interpretation and presentation in some
modules, uses mutable dictionaries for much of its model and changes process
working-directory/environment state during builds. It is not a concurrent,
multi-instance service. Future browser access needs a designed local interface;
calling a CLI does not deliver that interface or remove these limitations.

Saved generic yapic definitions, guided new-instance creation, actual quip
collection and live ai4X integration remain undelivered product work. Retaining
Python changes no source ownership, identity or acceptance rule. It does not
require preserving accidental module coupling or rewriting working features.

## Semantic responsibilities and dependency direction

Keep one Python application. Extract modules when they own a coherent subject or
remove a concrete dependency problem; avoid empty package hierarchies.

| Responsibility | Boundary |
| --- | --- |
| Semantic values and decisions | Stable identities, valid tracking/measurement values and pure subject rules; no filesystem, browser or provider execution. |
| Application operations | Shared use cases, bounded plans/results and narrow dependencies needed by CLI, agents and future graphical clients. |
| Source and host adapters | JSON/YAML/Markdown decoding, preservation, local files/processes and separately scoped provider access. |
| Projections and presenters | Derived selections and HTML/PDF presentation; consume facts and request shared operations without owning a synchronized source store. |
| Entry and composition | Parse interface intent, select the instance and concrete adapters, report expected failures and execute only authorized effects. |

These are design responsibilities, not a claim that the current source tree has
completed this separation. Parsing helpers and presentation escaping should have
clear owners; avoid importing a renderer merely to reuse a private helper.
Dependency cycles deserve a remedy tied to real change risk, rather than a bulk
module move to improve a graph statistic.

Core is shared responsibility, not a monolithic module. Repository inspection and
maintenance plans belong to shared operations; Git execution is an adapter.
Quip identification/collection belongs behind the same boundary; Pfm owns its
selection and explanation. A presenter does not write YAML directly. Private
integration experience must become synthetic evidence before entering public
code, tests or documentation.

## Precise Python values and checked construction

Separate external data from decoded and validated subject values. Use immutable
records, closed alternatives, precise collections and narrow protocols where
they earn a concrete guarantee. Introduce types at meaningful boundaries; do not
maintain a second typed model synchronized with an untyped implementation.

| Meaning | Required distinction |
| --- | --- |
| Activity | One managed work identity; versions do not become separate activities. |
| Objective and KR | Explicit subject identities and recorded evidence; observation counts do not supply measurements. |
| Instance | Durable identity independent of name/path remains a proposed contract. |
| Yapic definition/seed | Saved need, source references and composition; distinct from activity identity. |
| Placement | One appearance in a perspective; grouping/order implies no subject relationship. |
| Care binding | Actual accepted constellation/configuration reference, durable context and explicit association. |
| Assignment | Bounded authorized work with input/configuration provenance; separate from continuing care. |
| Observation/quip | Traceable work evidence with its own identity and qualification; never automatic achievement. |

The supported-activity hypothesis remains open. A candidate supported yapic links
an activity, seed and actual accepted care; ordinary Act/Pfm use requires none of
that invented care. Local proposals, accepted configurations and assignments are
different phases. A paused assignment does not dissolve care. Titles and local
labels need no artificial identity types.

`NewType` can distinguish identities for statically checked callers; it is not a
runtime identity validator or acceptance mechanism. `TypedDict` describes a shape
but performs no runtime decoding and prevents no mutation. A frozen dataclass is
shallow: retain owned immutable children or defensive copies wherever the API
promises immutability. Checked construction must validate the relevant source
and revision, rather than accepting a caller's boolean assertion of validity.

Tracking must preserve current authoring semantics:

- An unversioned activity may have no tracking or priority without status.
- Version entries require status; tracking forms must not be mixed, and every
  declared public version must be tracked exactly once.
- `released` forbids priority; `next` is allowed only with `on hold` and must
  satisfy the portfolio-wide uniqueness/rank constraints.
- Missing measurements remain unknown. Activity completion, Git commits, Todos
  and quips do not establish KR achievement or personal causal impact.

Represent valid alternatives clearly in checked code, then validate cross-source
constraints against the snapshot. Python's `bool` is an `int` subclass; schema and
numeric decoders must deliberately choose exact scalar kinds. Dates must satisfy
the promised canonical spelling as well as calendar validity. Static types cannot
prove that a referenced file exists, versions are complete or authority is current.

## Bounded type checking and runtime evidence

The draft's [mypy configuration](../mypy.ini) uses strict checking for
`outputs.py`, `source_values.py` and a positive contract fixture.
[Development requirements](../requirements-dev.txt) pin mypy 2.4.0.
`make typecheck` also runs the negative fixture through
[check_types.py](../dev/tst/check_types.py), requiring rejection of four invalid
calls/assignments. These are useful boundary checks, not full domain typing.
The remaining application modules are outside this static gate.

`outputs.py` checks path/publication call contracts. `source_values.py` owns
canonical date decoding from `object`. Neither module's annotations prove
filesystem safety or source validity by themselves. Behavioral tests must verify
redirected paths, malformed values and preservation of unrelated data.

Expand the gate in coherent slices when their subject contracts are designed.
Keep unchecked scope explicit. Do not manufacture a pass with blanket ignores,
`Any`, unchecked casts or reduced settings. Negative fixtures should reject the
specific misuse a type is meant to prevent; equivalent bad external JSON/YAML
needs runtime tests. Property tests search for counterexamples, not universal
proofs. No type gate or test count certifies the whole codebase.

## Shared operations, effects and recovery

Use this progression as a design boundary, not a delivered universal API:

```text
external input -> decoded value -> validated snapshot -> bounded plan -> outcome
```

A plan identifies intended changes, relevant revisions and effect boundaries.
Loading or saving data grants no execution authority. Expected outcomes distinguish
success, validation rejection, stale/conflicting state and, where applicable,
unavailable providers or uncertain external writes. A timeout after a provider
write cannot mean that retrying is safe. Exact error/result types need refinement
for each operation; no placeholder provider is required for local use.

Preserve unknown source content, comments and protected fields according to each
explicit operation's contract. Validate generated output ownership before reading,
writing or cleanup. Preflight rejects preexisting symlinks, hardlinks and special
files; it cannot exclude a noncooperating process replacing paths concurrently.
Revalidation
and atomic file replacement do not provide an atomic whole-tree transaction.
Watchers refresh views rather than protect writes.

The current process-per-instance design remains a boundary. Before exposing a
long-running local interface, define process isolation or explicit instance
context, serialization and conflict guarantees. Do not assume thread safety from
types or silently promote the current CLI into a multi-instance service.

Keep authoritative facts, saved view arrangements and transient interaction state
separate. A drag may request a tracking change or a placement move; the agreed
meaning decides which operation. Zoom and expanded branches are not new facts.
A proposed graphical client uses those shared Python operations, preserving a
complete CLI/editor/AI-host path and offline behavior.

## Durable definitions and guided creation

The [proposal](architecture-proposal.md#durable-definitions-and-identity) owns the
candidate data-only YAML and manifest vocabulary. Standard Act/Pfm and local
definitions should use one decoder and a static catalog of reviewed source,
operation and presenter IDs. Their executable behavior stays in application code.
A definition cannot name arbitrary imports, shell commands or new domain rules.
A dynamic plugin runtime is not selected.

Standard references resolve in the pinned application; local references name an
instance-relative definition. Origin/key/revision remain distinct, with no
filename-search shadowing or implicit merging. Unknown IDs and unsupported schemas
need actionable errors. Standard metadata lives once in application assets; do
not duplicate it as Python constants to synchronize.

Initial definitions must work without accepted care. The full proposed care
context retains selected cognitive capabilities, an AI-only team and all three
Operating Model parts, with rationale, gaps and source revisions. Actual accepted
provider configuration, serialization and activation require their own contract;
standard-definition care never becomes care of a personal instance automatically.

The proposed guided entry and explicit noninteractive arguments use the same
create/open operations. Creation needs a stable instance identity, protected
existing targets, valid empty sources, exact application selection and bounded
interruption/retry. Opening validates the selected instance without silently
migrating it, changing its pin or fabricating data/care. The current CLI opens an
existing instance; it does not yet implement this complete creation contract.

## Real quips and performance

[#8](https://github.com/normenmueller/yap/issues/8) owns actual quip collection.
Agree one accessible evidence source, qualification, activity association,
identity, original timestamps and deduplication. Repeated observations must not
become duplicate work, and missing observations do not prove inactivity. Preserve
free/bound terminology and explicit goal relationships. The existing illustrative
scene is not the persistent observation contract.

Measure performance using synthetic portfolios, recording fixture size,
interpreter, command and cold/warm conditions. Prefer removing redundant parsing,
subprocess launches and repeated traversals before adding a cache. Reuse an
invocation-local catalog only while preserving private workspace exclusion from
public models and durable caches. Cached values must account for all semantic
inputs and invalidation rules. An improved call count alone is not a measured
wall-clock speedup or a scale guarantee.

## Verification and product carryover

`make typecheck` checks its declared slice; `make test` checks existing behavioral
contracts and added regressions. Run the real publication toolchain when output
risk requires it. Verify source/configuration preservation, offline navigation,
stable publication destinations and bounded failures. Report the actual revision
and scope; this design text does not report unfinished implementation as verified.

The runtime uses Python 3.10-or-later syntax and POSIX facilities, including
`fcntl`; execution evidence currently covers Python 3.15.2. Neither a broader
Python-version matrix nor Windows portability is established.

The superseded #3/#4 language-replacement plan is closed as not planned after
acceptance of PR #14. Create/open and durable identity remain in #23, Act/Pfm
definitions/care in #12 and further domain/module quality work in #24. Shared
operations and compatibility remain obligations of those deliveries. Evidence for
an eventual creation/definition slice includes unknown
IDs, wrong pins, existing targets, interruption/retry and equivalent interactive
and noninteractive effects. Later adoption needs meaningful existing activities,
nested views, source writes, conflicts and comparison of accepted HTML/PDF output.
ai4X activation, complete view parity and adoption of existing portfolios remain
separately agreed work.

## Primary technical references

- [Python gradual type system](https://typing.python.org/en/latest/spec/concepts.html).
- [NewType behavior and limits](https://docs.python.org/3/library/typing.html#newtype).
- [TypedDict and other typing constructs](https://docs.python.org/3/library/typing.html).
- [Dataclasses and frozen-instance limits](https://docs.python.org/3/library/dataclasses.html).
- [Incremental mypy adoption](https://mypy.readthedocs.io/en/stable/existing_code.html).

</details>
