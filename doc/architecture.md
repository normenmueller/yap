# Application and instance boundaries

The current Python application is separated from the portfolio it operates on.
`python3 -m yap --instance PATH ...` selects one existing instance explicitly.
The CLI changes its process working directory to that instance; it is not a
multi-instance server. `dev/src/yap/resources.py` resolves templates and assets from
the application tree, independently of the selected instance.

| Owner | Content |
| --- | --- |
| Application | `dev/src/yap/`, `dev/acc/templates/`, `dev/acc/assets/`, tests and reusable documentation |
| Instance | `yap.json`, authored `pfo/`, saved `pov/`, private `.yap/cfg/` and generated `.yap/local/` |
| External workspace | Actual project work; accessed only through explicit private bindings and bounded operations |

The application does not search for a particular personal instance or copy itself
into one. Loading configuration does not create directories, initialize Git or
activate a provider. The current source distribution keeps application `dev/src/`
and `dev/acc/` together; wheel packaging is not implemented.

An optional instance manifest uses standard-library JSON:

```json
{
  "schema": 1,
  "slug": "my-portfolio",
  "branding": {
    "title": "My portfolio",
    "tagline": "Activities and outcomes"
  },
  "publication_prefix": "portfolio-"
}
```

`slug` selects the homepage filename (`my-portfolio.html`). Branding also accepts
`logo`, `favicon` and `footer` text; logo/favicon paths must name existing files
inside the instance. `publication_prefix` controls PDF destination prefixes;
preserve existing publication addresses deliberately when adopting older content.
Optional `sources.aspirations` selects an instance-relative aspiration root;
omitting it selects `pfo/asp`. The [authoring guide](authoring.md#objectives-and-key-results)
describes its structure, boundaries and the manual change from the previous default.
Manifest loading checks the setting's structure; content and build operations
validate the selected source filesystem before discovery or cache reuse.

Instance branding identifies the portfolio in its homepage, navigation, browser
context and selected logo/favicon. Application-owned mission, slogans and product
explanations remain unchanged. `about.html` describes the application and keeps the
label `Über yap.`. Its small product logo embeds the original application SVG bytes,
so an instance-selected image cannot replace the product identity. The footer
always contains the plain words `Focused with` followed by the product link `yap`
to About, with the same product wording in both interface languages. Optional
`branding.footer` supplies additional escaped plain-text credit before that link;
it defaults to empty and is never interpreted as markup or a curator API.
Optional `branding.footer_link` supplies one link within that credit. Inside
`branding`, the two values look like:

```json
{
  "footer": "Curated by Example",
  "footer_link": {"text": "Example", "url": "https://example.org/"}
}
```

Only the supplied `text` becomes a link. It must be nonempty, have no surrounding
whitespace and occur exactly once, case-sensitively, in the credit. The URL must
use HTTP(S), have a host and valid port, and contain no credentials, whitespace or
control characters. Invalid, missing or ambiguous link data leaves the credit as
escaped plain text. No credit is inferred from the link or its destination. The
application supplies no default curation attribution. Author information remains
with its source and is not rendered in the footer. No credit establishes agent
execution or accepted curation. The slogan `yap. That’s right!` belongs in the
user documentation rather than the footer. The product motto
`yap dein yapic mit mir!` remains on the homepage and About, independently of the
portfolio’s name; the current generic homepage does not add an inactive AI input.
Generic pages do not introduce personal requests or pretend that future need-entry
and trace collection are already available.

Optional `application.revision` is a full 40-character lowercase Git commit. When
declared, it requires that exact clean application checkout. The manifest does
not fetch or select another checkout; a launcher must select it explicitly.

The shared Python model feeds activity reports, boards, maps and goal views.
Entry points use the same source interpretation and operations. `pfo` owns facts;
`pov` owns arrangements. Generated views do not write inferred facts back to either.
Builds stage output before publishing a successful result. Private local bindings
belong in instance `.yap/cfg/machine.json`, not public Markdown or branding.

## Agent-assisted direction

The intended daily workflow combines a text editor, an AI host and deterministic
application operations. The person authors portfolio content and works in external
workspaces. An assisting agent can interpret requests and invoke the same bounded
operations as the CLI/UI. Validation, source ownership and effects stay in the
application rather than a second agent-maintained implementation.

Application-development memory lives in this application's `.ai4x/`. Each instance
needs its own thin agent entry and concise context describing its purpose, source
owners, selected application, authority and continuation. This is a bootstrap
contract; the CLI currently does not generate that instance memory. Do not copy
this application's development instructions as instance operational instructions.

AI assistance is possible without a formal ai4X association. A later accepted
constellation would bind selected cognitive capabilities, an AI-agent team and an
Operating Model containing Collaboration, Work Management and Governance Models.
Those values and their evidence belong to their authoritative configuration; an
instance should reference them rather than duplicate their ownership.

The coherent TypeScript replacement, saved generic yapic-definition contract,
guided instance creation and live ai4X curation adapter remain future work.
Ordinary saved data or generated agent context is not accepted ai4X curation.
Human acceptance, persistence, activation and individual assignment authority
remain distinct. Neither opening a portfolio nor a branding footer activates
agents or proves acceptance. An unbound ai4X association can coexist with ordinary
AI assistance.

The [next-architecture proposal](architecture-proposal.md) and its
[engineering appendix](architecture-engineering.md) retain the proposed
TypeScript and durable-definition design for issue #3. They are discussion
artifacts; this document continues to own the delivered Python boundary.
