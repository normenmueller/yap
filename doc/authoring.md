# Authoring portfolio sources

**English:** Keep facts in their source documents and arrangements in perspectives.
The examples below are synthetic; no activity, tracking value or goal is supplied
as a personal default.

**Deutsch:** Fakten gehören in ihre Quelldokumente, Anordnungen in Perspektiven.
Die folgenden Beispiele sind frei erfunden und keine persönlichen Vorgaben.

## Source owners

| Location | Owns |
| --- | --- |
| `pfo/act/**/FOLDER/FOLDER.md` | Explicitly marked activity or area identity and content |
| `pfo/act/act.md` | Report metadata, central activity tracking, explicit membership, dependencies and publication mapping |
| `pfo/nts/**/*.md` | Topic-filed notes; managed notes explicitly declare kind, key and title |
| `pfo/asp/goals.md` | Objective order and central Objective tracking |
| `pfo/asp/obj/KEY.md` | Objective identity, description and optional KR order |
| `pfo/asp/obj/KEY/*.md` | That Objective's Key Results and explicit contributions |
| `pov/NAME/.perspective.yaml` | Saved placement order, grouping and presentation choices |

Activities and areas use a same-named folder/document pair. Ordinary folders do
not become activities. Managed notes may be freely named files directly under
`pfo/nts/` or its topic folders. A note shortcut selects that document, not all its
siblings. Perspectives reference original sources rather than copies.

## Activities, areas and tracking

A source such as `pfo/act/design/design.md` begins with YAML front matter:

```yaml
---
key: design
kind: activity
title: Design a service
acronym: Design
board-caption: Service design
---
```

`kind`, unique stable `key` and `title` identify the entry. Keys use ASCII letters,
digits, hyphens and underscores, with slash-separated segments allowed. Each
segment begins with a letter or digit. A key is independent of its file path;
moving content creates no new identity or relationship. `#` denotes an anchor.
Use `kind: area` for a field description; areas have no activity tracking/cards.

Optional descriptive fields include `acronym`, `synonyms`, `subtitle`, `slogan`,
`board-caption`, `url` and `last-update`. Omit empty optional fields. Board/Map
labels use `acronym`, falling back to `title`; their optional subline comes only
from `board-caption`. `url` is a published source link, not a private workspace
path. Put `key` first and `last-update` last when present. Write free Markdown
after the header, beginning subsections at level two. Builds do not advance dates.

Central `pfo/act/act.md` can contain:

```yaml
---
title: Activities
tracking:
  design: {status: wip, priority: p2}
  research: {status: on hold, next: 1}
members:
  service: [design, research]
dgraph:
  spec: |
    research -> design
---
```

Every referenced key must exist. `members` alone declares semantic membership;
folders and perspective placement create none. A dependency arrow runs from
foundation to dependent activity. Explicit groups expand to eligible leaves;
self-edges and cycles fail validation.

Activity status values are `ibx`, `wip`, `on hold` and `released`. Priority is
`p1` through `p4`. Missing values remain unassigned, without inheritance or
aggregation. `released` forbids priority. Optional `next` is a unique portfolio
rank 1–3, allowed only for `on hold`; filtering does not renumber it. Tracking
belongs in this central document, not individual activity headers.

Public version sections remain parts of one activity:

```markdown
## v1 {#v1 .version}

Version content.
```

Track each public version centrally under `design#v1`, with an explicit status.
A versioned activity forbids additional activity-level tracking. Versions become
cards, not new activity identities, dependency endpoints or KR assignments.

## Perspectives and publication

Use `view check NAME` to inspect a perspective and `view save NAME` or
`view restore NAME` to preview changes; add `--apply` deliberately. Saved
`entries` control placement order. A source may appear in several perspectives.
`report-perspective: NAME` in `act.md` selects the saved report arrangement;
unplaced sources receive a runtime-only Unassigned projection. A normal build
does not save that addition into your perspective.

Relative links may need manual repair after moves. Explicit `publication` mappings
in `act.md` can preserve destination IDs and resource routes across source moves.
Attachments beside activity sources under `res/` are published resources, even
when linked only from source-only notes. Managed-note attachments are not exported
by default; they need explicit publication enrollment.

Source-only Markdown blocks use `::: internal` fences. They are removed from
published content; public links to their anchors are invalid. This mechanism
does not make neighboring attachments private. Local workspace bindings use the
source-owned map described below; they are excluded from publication.

## Local workspaces

An activity or area can declare local working directories in its initial YAML
front matter:

```yaml
wsp:
  code: "~/Repositories/example"
  proposal: "~/Repositories/example-proposal"
  shared-material: "~/Shelves/example"
  experiments: "../experiments"
```

Each name creates a shortcut at `wsp/NAME` beside that source document, including
for activities with modules. Names identify navigation only; they imply no
repository type, relationship, membership or tracking. Several names may share
a target. Nothing is inherited by children. Notes, Objectives, Key Results and
control documents do not own workspace maps.

Names begin with an ASCII letter or digit and contain only ASCII letters,
digits, hyphens or underscores. Duplicate names, including case variants, are
invalid. Values must be nonempty YAML strings: absolute paths, `~/` paths or
paths relative to the selected instance root. Relative paths retain that base
when a source moves. Paths are literal; URLs, environment-variable expressions,
other users' `~name` homes, backslashes and control characters are unsupported.
Quote paths, especially those containing YAML punctuation. An absent `wsp` or
`wsp: {}` declares no bindings.

`links` and builds reconcile declared shortcuts. Missing directories or mounts
produce local warnings and may leave dangling shortcuts; they do not prevent
validation or publication. An existing file target, navigation cycle, symlinked
`wsp` directory or collision with real content stops reconciliation. Workspace
targets are never traversed to discover sources or publish resources.

`wsp/` is reserved for local navigation. Undeclared shortcuts are preserved with
a warning because their ownership is unknown. After removing or renaming a map
entry, explicitly remove its obsolete shortcut. Real files and directories are
always preserved. Removing a binding does not delete the target directory.

The map is part of the instance's authored source and may enter its Git history;
the instance owner decides whether that is appropriate. Workspace metadata and
target contents are excluded from generated HTML, PDF, model caches and portable
site exports. This does not remove paths from source files or their history.

<details>
<summary>Migrating older machine bindings and navigation</summary>

Existing `.yap/cfg/machine.json` `links` entries are no longer a runtime source.
Run `workspace migrate` first to inspect the entire plan, then repeat it with
`--apply`. The migration copies `repo`, `shlf` and `zbox` bindings into each
source's `wsp` map under the same names. Rename them deliberately afterwards if
desired. It preserves relative path strings, unrelated YAML/body content and
unrelated machine settings. Existing same-target YAML entries are accepted;
conflicting values or shortcuts stop the preview before any write.

Verified old root shortcuts move to `wsp/NAME`; already matching shortcuts there
are reused. Real legacy-named files and unknown workspace shortcuts are retained.
An old root shortcut without a corresponding declared binding needs manual
resolution. No target directory is created, moved, scanned or deleted by migration.

Apply rechecks source, configuration and shortcut state. Source YAML and navigation
are completed before removing the old JSON `links` field. If an operation fails,
completed work remains; inspect the error and preview the migration again to
finish it. There is no automatic rollback over authored content. Automatic
source additions refuse aliased/anchored maps or other syntax they cannot edit
without changing existing meaning; edit those maps manually first.

</details>

## Objectives and Key Results

The default aspiration root is `pfo/asp`. To select another existing directory,
set an instance-relative path in the optional `yap.json` manifest (schema 1 and
the instance's `slug` remain required):

```json
{
  "schema": 1,
  "slug": "example",
  "sources": {"aspirations": "plans/aspirations"}
}
```

The selected root contains `goals.md` and, when Objectives exist, `obj/` with the
same structure shown below. It must be a real directory inside the instance,
separate from `.yap`, `.git`, `pov`, `pfo/act` and `pfo/nts` (including case
variants); symlink paths are not supported. Diagnostics name the selected location.

Existing instances using `pfo/okr` must either move that directory manually to
`pfo/asp` and repair affected relative links, or explicitly set
`sources.aspirations` to `pfo/okr`. There is no automatic move, fallback lookup or
source-directory creation. Normal validation and builds preserve authored sources,
configuration and perspectives. Publication destinations remain unchanged.

An Objective file needs stable `key` and `title`. Optional `timeline` and `url`
are authored values. Its tracking belongs in `goals.md`, with status `active`,
`on hold` or `closed` and optional priority `p1`–`p4`. `sequence` there orders
Objective keys; an Objective's optional `kr-sequence` orders its KR keys.

For `pfo/asp/obj/quality/verified.md`:

```yaml
---
key: verified
title: Verify the service against agreed criteria
measure: Recorded review against the agreed criteria
unit: review
target: 1
activities: [design]
---
```

The containing `quality/` folder determines its Objective, which must exist as
`quality.md`. Required KR fields are `key`, `title`, `measure`, `unit` and positive
`target`. KR keys use lowercase letters/digits separated by single hyphens and
are unique within the Objective. Optional fields include `metric`, `deadline`
(`YYYY-MM-DD`), `current`, `previous` and `activities`. Keep published KR content
in these fields; unknown fields and public body content fail validation. Use YAML
comments or source-only blocks for working notes.

Only record `current` or `previous` when supported by the stated evidence. Missing
measurements remain unknown, not zero. Closed status, commits and activity
completion do not prove achievement; there is no aggregate impact score.

KR contributions may be existing activity keys, Markdown links with absolute
HTTP(S) URLs, or objects containing only `title`. Managed keys are validated;
typos never become free text. Equal external URLs identify shared contributions;
title-only contributions remain local to their KR. These references do not gain
invented status or measurements.

Objective activity lists derive from the deduplicated union of explicit managed
KR contributions. Prose links, memberships, dependencies and version headings
create no additional goal assignment. A direct KR assignment to a parent activity
does not add its descendants. Run `check` after source changes.
