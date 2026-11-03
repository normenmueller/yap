# Working with an instance

Manage activities with a text editor and your instance's AI team. Describe the
view you need, examine the result together, and refine it in conversation.
The selected working model uses a terminal workbench, with no separate yap
management GUI. Generated views may be interactive, including drag-and-drop.

Open the same explicitly selected instance in both panes of a vertical split:

| Left pane | Right pane |
| --- | --- |
| A text editor, such as Vim, showing the instance's activity corpus | An AI host, such as Codex CLI, started from the same instance root |

The arrangement is a reference workflow; choose the editor and AI host that suit
you. The instance team's lead assistant coordinates the relevant expertise.
This is the intended model; automatic instance/team setup remains product work.
This first phase serves people comfortable with a terminal, editor and AI host.
It lets us learn from real use before considering a broader management interface.

## Develop a view together

For example, ask:

> Create Focus from my ongoing activities, grouped by topic. Show the recorded
> dependencies so I can see how the work connects.

The team clarifies the selection and topic assignments, reuses suitable tools,
and shows a first result. You might then ask for a landscape instead of a board,
or change the grouping. This can change a perspective's arrangement or create a
new presentation of that same perspective.

You describe the desired result rather than a JSON or YAML declaration. The team
can compose existing capabilities or develop a missing helper or presentation.
It preserves the agreed result so opening the view again does not require
designing it from scratch. **A saved view must remain executable:** the
conversation and a generated HTML file alone are insufficient. The files remain
inspectable and editable.

## Grow reusable capabilities

Each new view starts by looking for useful tools in the selected yap version and
the instance. Reuse or adapt them before creating another implementation.
Separate the view's personal content and settings from the underlying capability.

A tool developed for one instance can become a candidate for yap. Generalize it,
demonstrate it with synthetic data, and review it as an application change.
Once incorporated, future instances can use it through their selected yap
version. Local success does not automatically publish code or private content,
and existing instances keep their selected versions.

<details>
<summary>Persistence, shared rules and remaining design work</summary>

Preserve the view's purpose, selection, grouping, order, presentation implementation and required
dependencies. Where the team makes a cognitive assessment, retain its criteria
and basis and keep it distinguishable from recorded activity facts. Deterministic
refresh uses the saved rules and declared inputs; a new cognitive assessment is
a separate operation.

An editor buffer can contain changes the AI host cannot see on disk. Before
agent edits, save or reconcile the relevant changes; afterward, inspect and reload
external changes in the editor. Shared write operations must check the version
they read and reject stale changes. These are design requirements, not a claim
that choosing the same directory already prevents conflicting writes.

Facts and domain validation retain their common owners. A custom presentation
can request changes through shared operations; it does not create another
activity database. Direct PoV interaction and conversational changes follow the
same [move semantics](principles.md#meaning-of-a-move).

Local tool storage, execution, dependency handling and conflicting updates from
editor, AI host or interactive views still need concrete contracts. No universal
plugin framework or new persistence format is selected by this working model.

The instance's `.ai4x/` describes its operating team and context. This
repository's `.ai4x/` describes the team developing yap. Both use concise,
agent-facing, human-approvable instructions, with separate authority and state.
The [agent product contract](../.ai4x/PRINCIPLES.md) owns these constraints;
the [architecture proposal](architecture-proposal.md) explains their design.

</details>
