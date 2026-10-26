# Using yap / yap verwenden

*yap. That’s right!*

**English:** Edit your portfolio in Vim or another text editor, and use yap to
validate sources and generate activity and performance views. An AI assistant can
help through the same commands. Select your portfolio explicitly; its content
stays separate from this application.

**Deutsch:** Pflege dein Portfolio in Vim oder einem anderen Texteditor. yap prüft
die Quellen und erzeugt Ansichten zu Aktivitäten und Wirkung. Ein KI-Assistent
kann dieselben Befehle nutzen. Wähle dein Portfolio ausdrücklich aus; seine
Inhalte bleiben von der Anwendung getrennt.

Run from the application checkout, replacing the example instance path:

```sh
PYTHONPATH="$PWD/dev/src" python3 -B -m yap --help
PYTHONPATH="$PWD/dev/src" python3 -B -m yap --instance /path/to/portfolio check
PYTHONPATH="$PWD/dev/src" python3 -B -m yap --instance /path/to/portfolio open
```

`check` validates sources. `open` builds the selected portfolio and opens its
homepage. `all` builds the full output; `report` builds reports. Full report
generation requires Pandoc, LaTeX with `latexmk`, PDF utilities and a supported
Chromium-family browser. Python is the current runtime; the proposed TypeScript
replacement and guided instance-creation wizard are not delivered here.

Aspiration sources default to `pfo/asp`. Existing instances using `pfo/okr` need a
manual move or an explicit `sources.aspirations` setting before using this revision;
see [Objectives and Key Results](authoring.md#objectives-and-key-results).

Authored originals live under `pfo/`; arrangements and source shortcuts live
under `pov/`. Edit the original once, then choose its placements. Tracking belongs
to central control documents. Directories and visible grouping do not create
membership, dependencies, priorities or goal assignments. See
[authoring](authoring.md) for fields and examples.

The optional `yap.json` selects the homepage slug, branding and application
revision. A declared revision must match the exact clean application checkout.
Sources and private settings stay in the instance; generated output is under
its `.yap/local/`. The application source distribution needs `dev/src/` and
`dev/acc/` together. See [architecture](architecture.md).

Useful commands after `--instance /path/to/portfolio`:

| Command | Effect |
| --- | --- |
| `new "A useful idea"` | Creates a managed activity source. |
| `view check NAME` | Inspects a perspective. |
| `view save NAME` / `view restore NAME` | Previews a saved-perspective change; `--apply` executes it. |
| `init` | Restores existing saved perspectives and builds; it is not a new-instance wizard. |
| `links` | Reconciles private workspace-navigation shortcuts. |
| `workspace --help` | Lists explicit workspace setup operations and previews. |
| `export /path/to/new-export` | Builds and copies a portable site to a new directory outside the instance. |

Use the module's `--help` and command-specific `--help` for current syntax.
Workspace creation is a separate explicit operation; a build does not provision
external working directories. Check the command's preview and intended effects
before applying a write. Moving sources may require repairing relative links;
`check` diagnoses invalid references.

The retained interface currently uses German labels. Authored text retains its
language independently of future interface localization. Generated views and
work traces do not themselves prove goal achievement. Record measurements only
when their stated evidence supports them.
