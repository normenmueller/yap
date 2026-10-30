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
python3 -m venv .yap/local/venv
source .yap/local/venv/bin/activate
python3 -m pip install -r requirements.txt
PYTHONPATH="$PWD/dev/src" python3 -B -m yap --help
PYTHONPATH="$PWD/dev/src" python3 -B -m yap --instance /path/to/portfolio check
PYTHONPATH="$PWD/dev/src" python3 -B -m yap --instance /path/to/portfolio open
```

Python requires the dependencies in `requirements.txt` (PyYAML reads workspace
paths literally, without Markdown formatting). `check` validates sources.
`open` builds the selected portfolio and opens its
homepage. `all` builds the full output; `report` builds reports. Full report
generation requires Pandoc, LaTeX with `latexmk`, PDF utilities and a supported
Chromium-family browser. Python remains the application core until further notice;
the guided instance-creation wizard and saved generic yapic definitions remain
undelivered product work.

The runtime uses Python 3.10-or-later syntax and POSIX facilities, including
`fcntl`. Python 3.15.2 has been validated; other Python versions and Windows do
not yet have a verified compatibility matrix. Development setup and bounded
type checking are described in the [application README](../README.md).

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
| `workspace migrate` | Previews moving legacy machine bindings into source YAML; `--apply` executes it. |
| `export /path/to/new-export` | Builds and copies a portable site to a new directory outside the instance. |

Use the module's `--help` and command-specific `--help` for current syntax.
Workspace creation is a separate explicit operation; a build does not provision
external working directories. Check the command's preview and intended effects
before applying a write. Moving sources may require repairing relative links;
`check` diagnoses invalid references.

To bind a directory, choose the activity/area key and link name explicitly:

```sh
PYTHONPATH="$PWD/dev/src" python3 -B -m yap --instance /path/to/portfolio workspace attach /path/to/project --bind design --name code
```

Add `--apply` after reviewing the preview. `workspace create` accepts the same
binding options; `--template`/`--inputs` and `--git` are independent choices.
The command edits only the selected source binding and navigation; attach does
not modify the target directory. See [local workspaces](authoring.md#local-workspaces)
for path rules and migration.

The homepage centers the portfolio heading, a short introduction and a compact
assistant request preview. The heading link and underlined `yapics` open the
existing Activity/Performance collection. Select `yapic?` for a longer explanation:
with JavaScript it floats above the input and closes on outside click, Escape or
focus moving elsewhere; without JavaScript it opens in the page flow. Drag the
textarea's native lower-right grip to make it taller. Text remains in that same
field, but is not submitted or saved; its creation button stays disabled.

Optional `branding.assistant` supplies the displayed assistant name. Optional
`branding.assistant_credit` supplies an explicit display credit; when it contains
the configured `branding.footer_link.text` once, the existing safe credit-link
rules apply. Neither identity nor credit is inferred for an unconfigured instance.
For example, `"assistant": "Example helper"` and
`"assistant_credit": "by Example team"` are ordinary branding text, not a care
relationship or executable integration.

The homepage keeps the footer's product link to About and adds the discreet
`to yap ≈ quasseln` explanation on hover/focus. Use existing `branding.footer`
and `branding.footer_link` for an explicit credit. For example, a footer of
`Curated by Example.` with the matching safe link produces
`Curated by Example. Focused with yap.` on the homepage. Other views retain their
existing footer format; an unconfigured instance receives no curation credit.

The retained interface currently uses German labels. Authored text retains its
language independently of future interface localization. Generated views and
work traces do not themselves prove goal achievement. Record measurements only
when their stated evidence supports them.

### Illustrative collection cards / Illustrative Kartenangaben

The Yapics collection contains the existing Activities and Performance cards.
An instance can supply optional, explicitly authored **illustrative presentation
values** in its `yap.json`; they are not saved yapic definitions, collected quips,
measured growth or evidence of achievement. Only these selected display values
are rendered into the portable site; private `.yap/cfg/` settings are not a card
input. Use synthetic text for a public example:

```json
{
  "schema": 1,
  "slug": "example",
  "illustrative_cards": {
    "activity": {
      "need": {
        "paragraphs": [
          "Hello, example helper!",
          "Help me see which initiatives need my attention."
        ],
        "sender": "Example owner",
        "recipient": "Example helper"
      },
      "growth_label": "v0.42.7"
    },
    "performance": {
      "need": {
        "paragraphs": ["Welchen Beitrag kann ich nachvollziehen?"]
      },
      "growth_label": "v0.3.2"
    }
  }
}
```

Merge `illustrative_cards` into the existing manifest; keep its slug, branding,
application pin and other settings. Only `activity` and `performance` are
supported. Each card may have `need`, `growth_label`, both, or neither. A supplied
Need requires a nonempty `paragraphs` array of nonempty strings; optional `sender`
and `recipient` supply its byline without borrowing branding or another instance's
identity. Supplied names and labels must also be nonempty strings. Unknown fields,
`null` and wrong types are errors, reported before generated output is replaced.

Edit paragraphs in their original language; each array item remains a paragraph,
and line breaks within it remain line breaks. All values are plain text, never
HTML or Markdown. Missing Need, byline or label is omitted without invented
content. `growth_label` is the literal suffix in **Gewachsen bis …**; builds,
refreshes, application releases and work traces never update it. The field name
and this documentation record the illustrative provenance; no extra visible demo
badge is added. Future authoritative definitions/revisions remain #12's scope;
genuine quip identification remains #8's scope.

**Deutsch:** Ergänze den Block in der vorhandenen `yap.json`. Bearbeite für jede
Karte die Absätze unter `need.paragraphs`, bei Bedarf `sender`/`recipient` und das
feste `growth_label`. Entferne optionale Felder, um sie auszublenden. Die Angaben
sind bewusst verfasste Beispiele und werden mit der Website veröffentlicht.

**English:** Add the block to your existing `yap.json`. Edit each card's
`need.paragraphs`, optional `sender`/`recipient`, and fixed `growth_label`. Remove
optional fields to hide them. These deliberately authored examples are published
with the website.

Run the usual `report` build (or `open`/`export`) after editing. Configuration
changes participate in the existing incremental rebuild; unchanged inputs keep
the same labels. Need uses separate native disclosures: Tab to the control and
press Enter or Space. Tab into its text to scroll a long Need with the keyboard.
Both cards can be open together; opening one does not follow the card link and
works without JavaScript.
