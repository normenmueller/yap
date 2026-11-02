# yap product principles

yap should make activity management simple and offer expressive, independently
arranged views. The normal workflow combines direct interaction with a specialized
instance AI team and shared deterministic application operations.

These product decisions guide refinement, including
[#31](https://github.com/normenmueller/yap/issues/31). They describe the target;
the [user guide](README.md) and [current architecture](architecture.md) describe
delivered behavior. This is the human-facing explanation of the
[agent product contract](../.ai4x/PRINCIPLES.md). The
[architecture proposal](architecture-proposal.md#instance-ai-team) explains the
instance team's intended role and the remaining integration questions.

## Six principles

1. **Manage each activity once.** Its title, description, status and other facts
   remain the same across every perspective that includes it.
2. **Shape perspectives independently.** Focus and Overview may select, group
   and arrange the same activities differently without duplicating their facts.
3. **Preserve arrangement as authored work.** Manual order survives reopening.
   Placing a card higher does not itself assign a higher activity priority.
4. **Support direct interaction in views.** Generated PoVs may offer group
   selection, swimlane moves and card ordering. Everyday management uses the
   editor and instance team, without a separate management GUI.
5. **Start simply and expand when needed.** A new activity needs little input;
   a new perspective starts with useful defaults. Advanced visualization should
   not impose advanced administration on everyday work.
6. **Create and evolve views in dialogue.** The user describes the need and
   judges the result; the team and application core handle implementation and
   durable usability. Preserve each agreed view as an executable result, beyond
   the conversation or generated HTML. Editing JSON or YAML is not a prerequisite.

The [instance workbench](workbench.md) explains how editor, team and reusable
tools work together, including how a useful local tool can become a shared yap
capability.

<details>
<summary>Responsibilities, interaction decisions and open details</summary>

## Four responsibilities

| Concept | Responsibility |
| --- | --- |
| Activity | Own the work's identity, content and properties. |
| Perspective | Select activities and own their grouping and arrangement for a viewing question. |
| Presentation | Display a perspective as a board, map, list or dependency graph, with the relevant display settings and interactions. |
| Report | Deliberately compose selected content and presentations from one or more perspectives for a recipient. |

One perspective can have several presentations. A board and a map of Focus do
not become separate perspectives merely because they display it differently.
PDF and standalone HTML are report output formats.

## Manual and automatic order

Each perspective supports its own manual order or an explicitly selected
automatic sort, such as priority or status. Sorting one perspective must not
rearrange another. The order of sort values, tie handling and whether individual
presentations need separate ordering settings remain to refine.

On a board without swimlanes, cards can be manually ordered within each column.
With swimlanes, cards can be ordered within each column/swimlane cell, and the
swimlane rows can be ordered vertically. Automatic sorting must respect the
configured grouping boundaries.

Preserving the previous manual order while automatic sorting is active, and the
interaction for switching between those modes, are proposals still to agree.
Dragging during automatic sorting must have a defined behavior before delivery.

## Meaning of a move

| Action | Effect |
| --- | --- |
| Reorder a card within a column or swimlane cell in manual mode | Change this perspective's card order. |
| Move a swimlane up or down | Change this perspective's row arrangement. |
| Move a card between columns bound to activity status, for example In progress and Done | Change the activity's status; all perspectives use that same updated fact. |
| Move a card between freely named perspective groups | Change its placement in this perspective. |

Grouping by an activity property and grouping by a freely authored perspective
label have different effects. Presentation interactions must make the configured
meaning understandable. A placement move creates no activity dependency, domain
membership, priority or measured achievement. Example column labels do not
change the delivered status vocabulary.

## Reuse and dependencies

Adopt existing tools or libraries when their concrete benefit outweighs setup,
daily administration, integration and maintenance costs. References encountered
during discussion do not by themselves select a migration or dependency.

mdbase is excluded as a foundation or dependency for the current endeavor: the
considered capabilities offer no essential advantage for the selected workflow.
TaskNotes and Alexandrie are references, not selected replacements; evaluating
them is not a prerequisite to further yap refinement. This does not prohibit
future reuse supported by a concrete benefit.

## Refinement boundary

These decisions do not select a complete schema, instance directory layout,
browser API, AI provider or implementation scope. #31 retains the authoring,
perspective, presentation and report refinement. Guided instance creation,
durable care definitions and domain/module work retain their existing issue
ownership. No migration or provider activation follows from this document.

</details>
