# Yapic software design — discussion appendix

Technical appendix to the [authoritative proposal](architecture-proposal.md), owned by
[issue #3](https://github.com/normenmueller/yap/issues/3). Candidate boundaries and type
notation, not implemented APIs, schemas or approved implementation scope.

## Initial Scope And Later ai4X Integration

Act (Activity) and Pfm (Performance) are approved as standard yapics shipped with
yap. They use the same saved-definition, catalog and operation contract as other
yapics. The initial durable definition and guided instance creation are required
design work now. Actual ai4X curation, accepted care and activation remain later
integration; a saved `unbound` definition needs none of them.

The [authoritative proposal](architecture-proposal.md#durable-definitions-and-identity)
owns the candidate YAML, directory trees and full constellation-context semantics.
This appendix owns software boundaries and proof limits, not a second schema.

## Agent-Assisted Operation And Current Extraction

Agent-assisted portfolio management is the initial usage model: people author
content and work in their external workspaces; an AI host/team uses the shared
application operations for agreed management. Direct CLI/editor operation remains
available. This does not require an accepted ai4X care binding. Instance assistance
context and application development memory have different owners.

The delivered Python baseline owns workspace bindings in activity/area YAML
`wsp` maps, with named `wsp/NAME` navigation. Shared adapters must preserve that
source owner and the [authoring contract](authoring.md#local-workspaces), including
literal paths, bounded edits, explicit migration and exclusion from publication
and source discovery. Private application discovery is a separate concern.

The first practical separation retains the accepted Python implementation as one
reusable application. Replace code-location-derived instance roots with explicit
selection and resolve generic resources from the application. The personal
instance contains only sources/configuration and a thin invocation of an exact app
revision. Verify the empty instance and real consumer before daily adoption. The
TypeScript areas below describe its coherent later replacement, not an extra
implementation to synchronize or a prerequisite for physical separation.

The selected instance's homepage is `<slug>.html`. Open validates identity, pin
and source compatibility, preserves saved arrangements, refreshes derived output
as needed and opens that entry. It never infers team activation or grants mutations.

## Small Modules Before Many Packages

Begin with one TypeScript application project. Split packages only when an actual
independently reusable or published boundary needs it. Five possible source areas:

| Area | Responsibility |
| --- | --- |
| `model` | Subject identities, validated values, invariants and pure decisions. |
| `operations` | Shared use cases, bounded plans/results and the ports those cases need. |
| `adapters` | Files/Markdown and local host effects; Git, Todoist and later ai4X adapters only within their separately agreed delivery scopes. |
| `presenters` | Reusable projections and visual components selected by yapics. |
| `interfaces` | CLI, local interactive entry and composition of concrete adapters. |

This is a responsibility proposal, not a request to create empty folders or five
packages. Standard definitions live once in the application's
`dev/acc/yapics/`; their executable presenters/operations remain ordinary source
modules. Instance manifests select those definitions through the application pin;
instance-authored definitions and choices belong to the instance. Do not keep
parallel TypeScript metadata copies of the same YAML definitions.

Dependency rules: model knows no browser, provider or filesystem; operations use
model and narrow ports; adapters implement those ports; presenters consume typed
projections and invoke shared operations; interfaces choose concrete adapters.
Browser access reaches local effects through the explicit application boundary,
not by importing Node filesystem access into browser code. Check dependency rules
mechanically when implementation exists.

Core is a set of shared responsibilities rather than a monolithic directory.
Repository planning is shared; Git process execution is an adapter. Quip collection
can be shared; a Performance scene owns its selection and explanation. A presenter
never writes YAML directly or creates its own synchronized source store. Generic
perspectives/presentations live in the application; instances own selection,
parameters and authored arrangements. Public code/tests/docs know only generic
instances. Private integration data is explicitly selected through that same
boundary, never imported as a package or required fixture.

## Initial Definition And Instance Construction

Recommended candidate: data-only YAML plus a static catalog of released source,
operation and presenter IDs. This earns editable durable definitions while keeping
executable behavior in reviewed application code. A TypeScript-only definition
would be smaller for fixed compositions, but would not provide the requested
ordinary saved definition for subsequent development. A dynamic plugin runtime
would add unneeded distribution, loading and authority decisions. Choose one
metadata owner and the same decoder for standard/instance definitions.

```text
unknown YAML
  -> decoded definition
  -> definition validated against pinned application catalog
  -> instance-bound composition
```

Definition identity, activity identity, instance identity and ai4X project identity
are distinct. Create generates an instance key independent of display name/path.
Standard and local selections form a closed distinction: standard keys resolve
inside the pinned application, local selections identify an instance-relative
file. Origin/key/revision identify a definition; no filename-search shadowing or
implicit merging by key is permitted. Derive required IDs and inspected reference values through checked
construction, not assertions. Resolve source/operation/presenter references against
the pinned application revision and expected source kinds. Unknown references and
unsupported schemas give actionable diagnostics. YAML cannot name arbitrary imports,
shell commands or new domain rules. Listing an operation grants no execution or
filesystem/provider authority.

The initial definition can represent recorded absence of care (`unbound`). Future
local constellation proposals and actual accepted configurations are distinct
cases, not boolean flags on an invented team. The proposed constellation content
includes cognitive capabilities, an AI-only team and all three Operating Model
parts. References preserve the authoritative owner/revision; standard-definition
care does not inherit to a personal instance. Exact accepted-care fields remain
subject to the ai4X contract, whose concrete serialization is not yet defined.

One JSON instance manifest (`yap.json`) binds the selected app release and immutable revision to its
standard definition IDs and source roots. It does not mirror all definition data.
Default arrangements are part of the standard definitions; only an explicitly
saved personal arrangement creates `pov` content. Source facts stay in `pfo`.

The proposed `make yap` calls one local CLI; prompts and explicit arguments use
the same create/open operations available to a future UI. Create plans name,
location, pin, manifest and valid empty source files, validates the target, and
reports success only for a complete usable instance. Existing paths are protected;
partial outcomes remain distinguishable and retry cannot duplicate an instance.
Open checks identity, schema and pin without silent update/migration. A pin mismatch
requires the matching app revision or an explicit update decision, never fallback
to the current development head. Runtime checks establish filesystem/provider
facts; types alone cannot prove existence, completeness or continued availability.

## Semantic Values

The exact hypothesis is **“yapic as a supported activity”**, in German
**“yapic als betreute Aktivität.”** Supported means a dedicated accepted ai4X
constellation, durable care context and explicit continuing assignment capability.
It does not mean that an agent must be running or an assignment must be active.

| Value | Distinct meaning |
| --- | --- |
| Activity | One managed work identity and its explicit subject relationships. |
| Yapic seed | Durable need, source references and current development definition. |
| Supported yapic | Activity reference plus seed and dedicated care binding. |
| Care binding | Accepted constellation/project revision, durable context and explicit assignment references. |
| Assignment | Bounded authorized work using stated input/configuration revisions. |
| Artifact | Maintained output such as a perspective, presentation or document. |
| Placement | Occurrence of a source in one perspective, with local grouping/alias/order. |
| Provenance | Source/revision/time and, where applicable, producing assignment/configuration. |

The supported-yapic/care values below concern the later integration; Act and Pfm
do not need to construct `SupportedYapic` to open or work on shared facts.
A seed proposal is not yet evidence of established care. A paused assignment does
not dissolve an accepted care binding. Activity status, artifact readiness,
constellation acceptance and assignment status are separate subject meanings.
An ordinary Git observation must not require an invented AI assignment.

Illustrative TypeScript notation using current authored status names:

```ts
type VersionTrackingValue =
  | Readonly<{ status: "released"; priority?: never; next?: never }>
  | Readonly<{ status: "on hold"; priority?: Priority; next?: Next }>
  | Readonly<{ status: "wip" | "ibx"; priority?: Priority; next?: never }>;

type TrackingValue =
  | VersionTrackingValue
  | Readonly<{ status?: never; priority?: Priority; next?: never }>;

type ActivityTracking =
  | Readonly<{ kind: "activity"; value: TrackingValue; versions?: never }>
  | Readonly<{
      kind: "versions";
      versions: NonEmptyReadonlyArray<VersionTracking>;
      value?: never;
    }>;

type SupportedYapic = Readonly<{
  activity: ActivityId;
  seed: YapicSeed;
  care: AcceptedCareBinding;
}>;
```

The named component types and validated construction still require an accepted
contract; this excerpt is not delivered compilable code. Unversioned activities
can lack tracking or specify priority without status; neither absence is an invented
domain status. Version entries use `VersionTrackingValue` and always require status.
Positive type checks must cover priority-only activity tracking; negative checks
must reject a version without status. Constructors
check version anchors, completeness and uniqueness against the declared versions.
A nonempty type alone cannot establish those facts.

The public contract is stronger than a freely constructible exported record:
responsible modules expose inspected values and checked constructors, hiding
representation/brands where necessary. `ActivityId` and `Ai4xProjectId` have distinct
module-private nominal markers. Titles/local labels do not need artificial brands.
`SeedProposal`, `AcceptedCareBinding` and `SupportedYapic` are distinct phases;
`accepted`, `hasTeam` and `running` boolean combinations do not define the model.
A care constructor needs the actual accepted configuration reference, durable
context and explicit association, not a caller-supplied assertion of acceptance.

### Typed Transitions And Scope Of Proof

Proposed operation notation:

```text
unknown -> decoded source -> validated snapshot -> bounded plan -> execution outcome

establishCare(seed, acceptedConstellation, durableContext)
  -> Result<SupportedYapic, CareError>
planChange(validatedSnapshot, changeIntent)
  -> Result<ChangePlan, ChangeError>
apply(changePlan)
  -> Promise<ExecutionOutcome>
```

These are candidate contracts, not new provider APIs or approval machinery.
A validated snapshot binds checks to specific revisions. An accepted reference or
a plan type never creates human authority or proves that outside state remains
unchanged. Revalidation, replay/revocation rules and effect checks are dynamic.

Results distinguish success, validation rejection, conflict, provider unavailability
and an uncertain external outcome where applicable. A timeout after a remote write
cannot safely become "nothing happened; retry". Presenters and CLI handle closed
error variants exhaustively, including a `never` check for unhandled alternatives.

| Guarantee | Primary mechanism |
| --- | --- |
| Activity vs ai4X identity cannot be interchanged by ordinary typed callers | Opaque module-owned identity types and compile-time contract tests |
| Released tracking has no priority; next belongs only to on-hold tracking; exclusive tracking forms | Closed unions, forbidden counterfields and checked constructors |
| External fields and source structure are valid | Runtime decoding from `unknown` |
| Referenced versions exist, all are tracked and global next values are unique | Subject/snapshot validation |
| A supported yapic has actual accepted care and durable context | Checked care construction against authoritative artifacts |
| Sources/authority are still current and effects have known outcome | Runtime revision/effect validation and explicit result handling |

TypeScript is structurally typed and intentionally not fully sound. A discriminant
alone does not guarantee exact object shape for arbitrary values. `any`, unchecked
assertions and unchecked deserialization must not bypass subject boundaries.
Use assertions only at reviewed construction/interop points with evidence.

`Readonly` is shallow and mutable aliases can invalidate an apparent read-only
value. Constructors take ownership through controlled values/defensive copies as
needed; readonly APIs and tests support the contract. TypeScript does not prove
purity, linear use of a plan, or filesystem/provider concurrency guarantees.

### Compiler And Contract Checks

Proposed baseline: pinned TypeScript version; `strict`,
`exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`, `noImplicitReturns`,
`noFallthroughCasesInSwitch`, and a dedicated full typecheck. If compilation emits
code, failed typechecks must block release/build acceptance; transpilation alone
is insufficient. Evaluate upgrades deliberately.

Negative compile-time tests should reject mixed tracking forms, prohibited fields,
interchanged identity types and operations on the wrong phase. Runtime decoder
tests reject equivalent invalid YAML/JSON values. Snapshot tests cover global
constraints. Property tests seek counterexamples to laws; they are not universal
mathematical proofs. Each advanced type construction must name a concrete subject
guarantee it earns.

## Editing And View State

Keep authoritative facts, saved view arrangements and transient interaction state
distinct. Zoom, expanded branches and an in-flight drag preview are not new
portfolio facts. A drag may request `changeTracking` or `movePlacement`; its agreed
semantics decide which operation. Both CLI and UI use the same operation.

A write request identifies the target, intended change, relevant source revisions
and effect boundary. Return success, a meaningful validation error or an explicit
conflict. The file adapter applies the smallest intended source change while
preserving unrelated prose and protected fields. Comment/formatting guarantees
must be decided for each explicit save operation rather than promised globally.

Serialize application writes and check revisions. Hash-then-replace still races
against a noncooperating Vim writer. Define the actual detectable-conflict/recovery
guarantee; a stronger claim requires an accepted cooperative protocol. Watchers
refresh views and never serve as transaction protection.

## Proportionate Verification

Use discriminating behavioral/law tests and boundary failures, not tests that mirror
code structure. Candidate laws include: projections do not mutate sources; placement
changes do not alter subject relationships; supported save/load preserves promised
meaning; CLI/UI operations produce equivalent subject effects; repeat provider
observations retain identity rather than duplicate work.

The first planned implementation is #4's empty-instance foundation after #3's
scope decision. It enables the initial Act/Pfm direction without delivering a
full board or Performance replacement. Refine executable guided create/open,
immutable pinning and initial definition save/load with #12 before approving
#4's delivery scope. ai4X need entry, accepted-care persistence and activation
remain later work; no placeholder provider or fabricated care is required.
For that foundation, verify a genuine empty instance, standard/own definition
resolution, unknown IDs, pin mismatch, existing targets and interrupted creation;
exercise the same operations through interactive and noninteractive CLI entry.
Later bounded evidence should include one versioned activity in two views, nested
lanes, a meaningful write, provider unavailability and an external-editor conflict.
Compare existing/candidate appearance before accepting changes. No test of an
unimplemented component is claimed by this appendix.

## Primary technical references

The following links support the candidate TypeScript guarantees and their limits;
implementation must verify its chosen compiler version and actual runtime boundary.

- [Narrowing and exhaustiveness](https://www.typescriptlang.org/docs/handbook/2/narrowing.html).
- [Structural compatibility and soundness limits](https://www.typescriptlang.org/docs/handbook/type-compatibility.html).
- [Object and readonly types](https://www.typescriptlang.org/docs/handbook/2/objects.html).
- [Unique symbols](https://www.typescriptlang.org/docs/handbook/symbols.html).
- [Compiler configuration](https://www.typescriptlang.org/tsconfig/).
