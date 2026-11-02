# Product constraints for agents

Apply these owner-selected constraints to product refinement, design and review.
They specify target behavior, not delivered functionality or execution authority.
Verify current behavior in source and the owning Issue before proposing changes.

## Invariants

- Manage each activity once. Preserve stable identity and shared facts across
  perspectives; never copy facts to make another view.
- Keep perspectives independent. Selection, grouping and manual/automatic order
  in one perspective must not rearrange another.
- Treat saved arrangement as authored data. Preserve it across reopening; never
  infer activity priority from visual position.
- Support direct interaction in generated PoVs, including grouping, swimlane
  moves and card order. Do not build a separate management GUI in the selected
  working model. Keep readable files as an additional editing path.
- Minimize required input and administration. Provide useful initial defaults;
  advanced visualization must not require advanced everyday administration.
- Create and evolve views in dialogue. The user describes the need and judges
  the result; the team and core own implementation and durable usability.

## Responsibility boundaries

| Concept | Owns |
| --- | --- |
| Activity | Work identity, content and shared properties. |
| Perspective | Activity selection, grouping and arrangement for a viewing question. |
| Presentation | Board/map/list/graph rendering, display settings and interactions. |
| Report | Deliberate composition of content and presentations from one or more perspectives. |

Keep all four explicit. Multiple presentations of one perspective do not create
new perspectives. PDF and standalone HTML are report output formats.

## Ordering and move effects

- Support per-perspective manual order and automatic sorting by properties,
  including priority or status. Automatic sort respects grouping boundaries.
- Manual board order without swimlanes: within a column. With swimlanes: within
  each column/row cell. Swimlane rows can be ordered vertically.
- Card reorder in manual mode -> update this perspective's order only.
- Swimlane reorder -> update this perspective's row arrangement only.
- Move between status-bound columns -> update shared activity status; every
  perspective reads the updated fact.
- Move between freely named perspective groups -> update placement here only.
- Distinguish property-bound grouping from perspective labels before executing
  a move. Make the interaction's effect understandable to the user.
- Never derive dependencies, domain membership, priority or achievement from a
  placement move. Example column labels do not redefine current status values.

Open: sort-value order, ties, per-presentation settings, manual-order retention
across mode changes and dragging during automatic sorting. Do not promote these
open details or earlier assistant suggestions to accepted requirements.

## Instance workbench and conversational authoring

- Use a terminal workbench: editor (for example Vim) on the instance corpus in
  one pane, AI host in another. Start both from the same explicitly selected
  instance root. The left/right vertical split is the reference arrangement;
  no particular editor, terminal multiplexer or AI host is mandated.
- Keep management lean through editor, conversation and shared operations.
  Generated PoVs may be interactive, including drag-and-drop; this does not
  select a separate management GUI, embedded editor or bundled AI host.
- Do not require users to author JSON/YAML to create or revise a PoV. The team
  handles persistence format and implementation; preserve inspectable artifacts.
- Distinguish recomposing an existing perspective, developing a presentation,
  and making a cognitive assessment. Keep all four responsibility boundaries.
- Reuse or adapt existing helpers from the selected application/instance before
  creating new ones. Local tools may extend presentation capabilities beyond
  the standard catalog; do not constrain all PoVs to preinstalled renderers.
- Preserve the agreed purpose, selection/group/order rules, cognitive decisions and their
  basis, presentation/tool sources, required versions/dependencies and relevant
  execution inputs. An executable saved view is essential; chat or generated
  HTML alone is insufficient. Reopening must not require generative redesign.
- Require deterministic replay for the agreed deterministic parts under the same
  declared inputs/conditions. Distinguish refresh from cognitive reassessment;
  retain assessments as traceable judgments, not inferred activity facts.
- Keep shared facts and domain validation in common operations. Local tools must
  not establish a competing source store or silently bypass move semantics.
- Account for editor buffers and competing writes. Before agent edits, reconcile
  relevant unsaved editor changes; before operation writes, verify the read
  revision and reject stale state. Surface external changes for editor reload.
  Starting at the same root does not provide conflict control; exact mechanics
  remain to design. Do not claim unsaved buffers are detectable from disk alone.
- Separate portfolio-specific content/configuration from reusable capability.
  Evaluate new tools for generalization; do not create a fresh implementation
  for every PoV when an existing tool can be reused or extended.
- Return suitable generalized tools to yap through a separate application change
  and normal review, with synthetic examples and no private instance material.
  A local tool is not automatically an application feature. Future instances use
  the reviewed capability through their selected application revision; do not
  update instance pins or publish local content implicitly.

Open: local tool location/reference/runner/dependency contracts, source update
conflicts between editor/host/interactive PoVs, and criteria for upstream reuse.
No universal plugin runtime, persistence schema or script language is selected.

## Instance team and deterministic core

- Design normal instance use around a specialized AI team with a dedicated lead
  assistant. Treat the team as a core product component.
- Assign cognitive interpretation, proposals and coordination to that team;
  keep validation and bounded execution in shared deterministic operations.
- Share operations across agents, CLI and UI; do not build a second fact store or
  agent-maintained implementation of application rules.
- Instance `.ai4x/` owns team instructions/context; `.yap/` owns local settings
  and runtime. A selected AI host/provider executes agents. Files alone neither
  run agents nor establish accepted care or authority.
- Preserve manual/scripted use to a supported extent. Full intended experience
  assumes the instance team; continuous background execution is not required.
- Distinguish application-development `.ai4x/` (build and maintain yap) from
  generated instance `.ai4x/` (operate its selected portfolio). Keep team identity,
  instructions, authority, state and runtime independent; never copy development
  workflow into an instance or synchronize the contexts.
- Apply BEHAVIOR's agent-first, agent-facing, human-approvable formulation/content
  principles to both contexts. Shared writing principles do not imply shared
  instructions or authority.

Open: creation/bootstrap, exact directory layout, lead role, provider binding,
memory and authority contracts. Treat `act`/`pov` as responsibility examples, not
approval to migrate `pfo/act`. Preserve #23/#12/#24 ownership; no activation or
implementation scope follows from this direction.

## Reuse decisions

- Adopt external tools only for a concrete net benefit after setup, integration,
  daily administration and maintenance costs.
- Exclude mdbase as a foundation/dependency for the current endeavor.
- TaskNotes/Alexandrie are references, not selected replacements or prerequisite
  evaluations. Future justified reuse remains possible.

## Documentation ownership

This file owns the product constraints agents must apply. [BEHAVIOR](BEHAVIOR.md)
owns agent working rules; [STATE](STATE.md) owns continuation. Issues own delivery
scope, Project metadata owns live status/order, implementation owns current facts.
[Human product principles](../doc/principles.md) explain this contract;
[human workbench model](../doc/workbench.md) explains instance use and tool reuse;
[human architecture proposal](../doc/architecture-proposal.md#instance-ai-team)
explains the target team architecture. Reconcile explanations when constraints
change; do not maintain competing decisions in both audiences' documents.
