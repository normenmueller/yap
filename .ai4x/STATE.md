# Return point — architecture discussion and product review

This is issue-linked `docs/3-architecture`, containing the generic discussion
proposal for [#3](https://github.com/normenmueller/yap/issues/3), based on published
trunk. [Proposal](../doc/architecture-proposal.md) owns future design choices;
[engineering appendix](../doc/architecture-engineering.md) owns candidate module,
value and proof boundaries. [Current architecture](../doc/architecture.md) owns
delivered Python behavior. No private instance data or history is imported.

Next: discuss the smallest testable create/open and durable-definition slice.
Standard Act/Pfm, agent-assisted operation and one-way instance dependency are
product directions; exact identity, persistence and public APIs still require
agreement. This proposal does not approve implementation, migration, activation
or full view replacement. [#4](https://github.com/normenmueller/yap/issues/4)
remains separately scoped foundation work after the architecture decision.

The independent branding candidate remains in
[PR #2](https://github.com/normenmueller/yap/pull/2) for
[#1](https://github.com/normenmueller/yap/issues/1), pending owner acceptance.
Its 244-test evidence applies to that implementation; this documentation branch
changes no runtime/resources/tests. Do not merge that candidate or start a new
feature merely to tidy the branch list.

The application Project owns live status/order. Future care references remain
[#12](https://github.com/normenmueller/yap/issues/12); README improvements remain
[#13](https://github.com/normenmueller/yap/issues/13). Read their source scope rather
than duplicating a delivery queue here. BEHAVIOR owns recovery and authority.
