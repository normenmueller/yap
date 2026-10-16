# Repository starter sources

These files are portable source material for the `general` and `db-gitlab`
profiles. [Deutsche Anleitung](README.de.md).

`base/` owns the shared files. `gitlab/db/` adds the unchanged DB LICENSE and
the metadata skeleton; it does not maintain a second project README.
`ai4x-footer.html` is the optional shared attribution. The Python renderer at
`yap.repo_templates` reads these files without invoking Git or writing a target.

## Manual use without yap

1. Choose German (`de`), English (`en`), or both. For both, explicitly choose the
   primary language. Copy the selected `base/README.<language>.md` to `README.md`
   and the other to `README.<language>.md`; do the same under `doc/`. Do not copy
   an unselected language. Copy `AGENTS.md`, `.gitattributes`, `.gitignore` and
   all three `.ai4x/` files unchanged initially.
2. Fill the named fields in the copied files as literal Markdown text. Escape
   Markdown punctuation and HTML where needed. `title`, `purpose`, and `maintainer`
   are authored project inputs; purpose or contact may explicitly remain open.
   In each language's README, `readme` is that language's resulting filename.
   `alternate_link` is a link to the counterpart in the same directory, or empty
   for a monolingual project. `languages` and `primary_language` in CONTEXT record
   the explicit selection. Keep agent files in English.
3. For the general profile, leave `db_structure` and `db_authority` empty and set
   `license_notice` to “Not selected yet.” or “Noch nicht festgelegt.” If supplying
   a license explicitly, create `LICENSE`, link it from the license notice, add
   `LICENSE -text` to `.gitattributes`, and record its authority in CONTEXT.
4. For DB, copy `gitlab/db/LICENSE` without editing its bytes. Review and confirm
   every proposed metadata value for this repository before filling the copied
   `scm-info.yaml`. Its fields accept YAML strings or string lists; JSON-quoted
   strings and arrays are valid YAML and avoid interpreting punctuation as syntax.
   Keep `version: v3` and `license: LicenseRef-DBISL`. The field
   `custom_confidentiality` fills the nested confidentiality value. Add the DB
   license/metadata description to `db_structure` and `db_authority`, link LICENSE
   in `license_notice`, and add `LICENSE -text` to `.gitattributes`.
5. Fill `copyright` explicitly. The confirmed personal suggestion is
   `© 2026 Project contributors`; change the owner,
   profile link, or year when appropriate. Do not advance the year automatically.
   Replace `footer` with the contents of `ai4x-footer.html`, or leave it empty
   when explicitly omitted. Leave no unresolved template fields.

These steps create no Git repository, commit, remote, server protection or push.
`protected-branches` describes metadata; it does not configure the hosting server.
The DB metadata baseline is structurally checked, not certified against an
independently verified internal DB schema or policy.

## Renderer input contract

`render_template(profile, inputs)` returns a sorted mapping of relative POSIX
paths to bytes. It never modifies inputs or writes destination files. Unsupported
profiles/fields, unresolved template fields, unsafe source paths and invalid
values raise `ValueError`.

| Input | Required value or default |
| --- | --- |
| `title` | Required nonempty single-line plain text. |
| `languages` | Required list: `["de"]`, `["en"]`, or both once each. |
| `primary_language` | Required `de` or `en`, included in `languages`. |
| `purpose`, `maintainer` | Optional objects keyed only by selected languages; values are nonempty plain text, possibly multiline. Missing entries explicitly remain open in that language. |
| `copyright_holder` | Optional single-line text; default `Project contributors`. |
| `copyright_year` | Optional integer 1–9999; default `2026`, never derived from the clock. |
| `copyright_url` | Optional HTTP(S) URL without credentials/whitespace, or empty string. Defaults to an empty string; supply a chosen public profile explicitly. |
| `ai4x_footer` | Optional boolean; default `true`. |
| `license_text` | General only: optional nonempty text copied to LICENSE exactly as UTF-8, including its original trailing whitespace. Omission selects no license. |
| `db_metadata` | DB only: required complete metadata object, described below. |
| `db_confirmed` | DB only: must be the boolean `true` after this repository's complete values were reviewed. |

DB metadata requires `version: "v3"`, `license: "LicenseRef-DBISL"`, nonempty
string lists for `contacts`, `reference-ids`, `protected-branches`, and
`usage-scenario`; a nonempty string for `confidentiality`; and `custom` with
nonempty `integrity`, `availability`, and `confidentiality` strings. No additional
keys are accepted. Other value enums are not invented without an authoritative
schema. The renderer safely serializes values as data.

`defaults()` returns a fresh copy of the common copyright/footer suggestions and
the complete proposed DB metadata. It supplies neither project languages nor DB
confirmation. After successful render validation, `resolved_inputs(inputs)`
provides effective common defaults and explicit open purpose/contact entries for
display. It never adds DB metadata or confirms it on behalf of the user.

Example general input:

```json
{
  "title": "Project example",
  "languages": ["en"],
  "primary_language": "en",
  "purpose": {"en": "Describe the intended outcome."},
  "maintainer": {"en": "Project team"}
}
```

Git initialization, local bindings and any publishing are separate explicit
operations. Generated files belong to the target project; later template changes
do not update existing repositories.
