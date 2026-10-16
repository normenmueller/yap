# Application context

yap is a reusable activity-portfolio application. It reads one explicitly selected
instance per process. The current extracted implementation is Python; a coherent
TypeScript replacement is a future direction, not a delivered runtime.

- [User guide](../doc/README.md): current commands and daily operation.
- [Authoring](../doc/authoring.md): source owners, fields and synthetic examples.
- [Architecture](../doc/architecture.md): application/instance boundary and target
  agent-assisted operation.
- [TEAM.md](TEAM.md): development expertise and review routing.

`dev/src/yap/` owns implementation, `dev/acc/` application templates and assets,
`dev/tst/` regression evidence and `doc/` reusable guidance. Root AGENTS.md is a
thin entry point; this `.ai4x/` owns application-development context.

Instances own `yap.json`, `pfo/`, `pov/`, private `.yap/cfg/` settings, generated
`.yap/local/` output and their own agent context. They select application code;
application code must not embed a particular instance or know its location.

Activities retain explicit stable identities. Relationships, status and measured
achievement are never inferred from directories, prose, Git activity or views.
The initial extracted application does not deliver saved generic yapic definitions,
an ai4X curation adapter or an accepted constellation. Preserve these distinctions
when extending the product.

The application owns its own `.yap/local/` for ignored development evidence and
caches. This is distinct from every selected instance’s `.yap/`; do not share or
synchronize agent memory, configuration or runtime directories between them.

The canonical application repository is `normenmueller/yap`; the root `LICENSE`
owns the selected Apache-2.0 terms. Verify actual branch/publication state.
The compact directory convention is `doc` and `dev/{src,tst,acc}`; add `utl` only
when real helper tools need it. Ordinary documents use lowercase filenames;
README and agent entry/contract filenames retain their established conventions.
