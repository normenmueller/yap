# yap — your activity portfolio

Reusable portfolio rendering and local operations, separated from instance data.
This candidate retains the accepted Python implementation; the planned TypeScript
replacement and guided onboarding are separate work.

Run from this application checkout:

```sh
python3 -m venv .yap/local/venv
source .yap/local/venv/bin/activate
python3 -m pip install -r requirements.txt
PYTHONPATH="$PWD/dev/src" python3 -B -m yap --instance /absolute/path/to/portfolio check
PYTHONPATH="$PWD/dev/src" python3 -B -m yap --instance /absolute/path/to/portfolio report
```

`open` validates the selected application pin, builds the portfolio and opens its
instance homepage. A declared `application.revision` requires the exact clean Git
checkout; private application-path discovery belongs to the instance launcher.

The existing Pandoc, LaTeX, PDF utilities and Chromium-family browser are required
for full reports. Application code and templates stay here; authored portfolio data,
private configuration and generated output stay in the selected instance. Do not
copy application code into an instance. This source distribution must keep `dev/src/`,
`dev/acc/` and `requirements.txt` together; wheel packaging is not implemented by
this candidate.

An optional instance `yap.json` uses schema 1, a simple `slug` for its homepage,
and `branding` text fields `title`, `tagline`, `logo`, `favicon` and `footer`.
Logo/favicon paths must identify existing files within the instance. A deliberate
`publication_prefix` can preserve established PDF destination addresses. Loading a
manifest does not initialize Git, migrate sources or activate an agent/provider.
The core source layout remains `pfo` and `pov`. Local workspace bindings belong
in each activity/area's YAML `wsp` map; generated navigation is always `wsp/NAME`.
Existing machine bindings need an explicit previewed migration; see
[workspace authoring](doc/authoring.md#local-workspaces). Runtime output remains
in `.yap/local/`.

Run regression tests with `make test`. The CLI supports one selected local instance
per process; it retains the baseline process working-directory model.

## License

Licensed under the [Apache License 2.0](LICENSE). Bundled repository-template
license texts retain their stated terms.
