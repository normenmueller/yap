# Return point — architecture discussion on the accepted Python baseline

This is issue-linked `docs/3-architecture`, with the generic discussion proposal
for [#3 / draft PR #14](https://github.com/normenmueller/yap/pull/14). The owner is
requested as reviewer. [Proposal](../doc/architecture-proposal.md) owns future
choices; [engineering appendix](../doc/architecture-engineering.md) owns candidate
module/value/proof boundaries. [Current architecture](../doc/architecture.md)
owns delivered Python behavior. No private instance data or history is imported.

A fresh session explicitly opened here can continue the architecture discussion;
`trunk` provides the accepted application and waits for the owner's next work
choice. Verify actual Git, worktree, remote and review state. Recovery needs no
previous chat or special resume command. BEHAVIOR owns completed-feature cleanup.

Next: discuss the smallest testable create/open and durable-definition slice.
Standard Act/Pfm, agent-assisted operation and one-way instance dependency remain
product directions; identity, persistence and public APIs still need agreement.
Reconcile the candidate manifest's `sources.goals` vocabulary with the delivered
`sources.aspirations` contract before refining the next implementation scope.
Publishing this draft does not approve implementation, migration, activation or
full view replacement. [#4](https://github.com/normenmueller/yap/issues/4) remains
separately scoped foundation work after the design decision.

The owner accepted #1 / merged PR #2 and #15 / merged PR #16. This branch
incorporates the accepted `pfo/asp` default and optional `sources.aspirations`
selection from `trunk`; no additional runtime behavior is introduced here.
All 254 regression tests and real synthetic HTML/PDF/browser checks passed at
implementation revision `cf57907`. Runtime/resources/tests retain those bytes;
reuse that evidence for this integration and its documentation-only changes.
Earlier architecture review applies to its inspected proposal artifacts and is
not acceptance of future API/runtime changes. PR #14 remains a draft.

The application Project owns live status/order. Care references remain #12 and
README improvements #13; read their owning scope instead of duplicating a queue.
BEHAVIOR distinguishes design acceptance, implementation acceptance and merge
authority. No consumer revision or instance migration is selected by this handoff.
