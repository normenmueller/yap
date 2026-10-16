# Return point

The reusable application uses `normenmueller/yap`. Inspect actual Git/remote state;
this checkout is the issue-linked `fix/1-portfolio-branding` review branch for
[#1](https://github.com/normenmueller/yap/issues/1), based on published `trunk`.
The owner’s Apache-2.0 initialization and generic application history are retained.

The branding correction preserves fixed product copy, signature and original
product logo while portfolios select their own identity and optional author.
[Architecture](../doc/architecture.md) owns that contract. All 240 tests pass,
including author escaping, German/English bylines, asset-name isolation and real
browser/PDF integration. Independent code review found no material blockers;
a synthetic external instance completed a full report and desktop/narrow browser
checks of home, collection and About. Consumer-specific verification belongs to
the selecting instance’s records.
Evidence stays ignored under `.yap/local/build/`.

Next: review [PR #2](https://github.com/normenmueller/yap/pull/2), natively
associated with #1, for product acceptance. The universal homepage/About motto
remains independent of a portfolio’s name.
Do not merge or update another checkout without that acceptance. Verify live PR
and publication state; memory does not establish approval. The implementation is
Python. TypeScript replacement, a new-instance wizard, saved generic yapic
definitions and live ai4X integration remain undelivered. Application and instance
agent/runtime contexts stay separate; no private instance is authoritative here.
