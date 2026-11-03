# Your activity portfolio

## Why

Keep sight of what matters and decide what deserves your attention, with little
administrative overhead.

## What

The intended workflow keeps activity management simple: manage each activity
once and shape independent perspectives on your work. Present them as boards,
maps or lists, then compose selected content and presentations into shareable
reports.

## How

**yap** is the tool for this approach. It keeps your portfolio in readable files
and uses shared, deterministic operations. The intended workbench pairs a text
editor with a specialized AI team, led by a dedicated assistant, in a terminal
split. Develop views in dialogue, using and extending reusable tools. Generated
views may be interactive; no separate management GUI is planned.

Today, the Python application validates an existing portfolio and generates
views and reports. Guided creation, instance-team provisioning and conversational
view development remain product goals.

Start with the [user guide](doc/README.md) for setup and commands. Read the
[product principles](doc/principles.md) for the intended experience and the
[workbench model](doc/workbench.md) for the working approach.

<details>
<summary>Developing yap</summary>

After following the user guide's environment setup:

```sh
python3 -m pip install -r requirements-dev.txt
make typecheck
make test
```

The type check covers a declared subset of the codebase. See the
[Python engineering guide](doc/architecture-engineering.md) for its scope.
The repository's development team and each portfolio's operating team have
separate contexts, governed by the same agent-facing writing principles.

</details>

Licensed under [Apache 2.0](LICENSE). Bundled template licenses retain their terms.

© 2026 [nemron](https://github.com/normenmueller)
