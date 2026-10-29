# Return point — architecture discussion on the accepted Python baseline

This is issue-linked `docs/3-architecture`, with the generic discussion proposal
for [#3 / draft PR #14](https://github.com/normenmueller/yap/pull/14). The owner is
requested as reviewer; no submitted GitHub review was present at recovery.
[Proposal](../doc/architecture-proposal.md) owns future choices;
[engineering appendix](../doc/architecture-engineering.md) owns candidate
module/value/proof boundaries. [Current architecture](../doc/architecture.md)
owns delivered Python behavior. No private instance data or history is imported.

The owner selected #3 after completing #18. This fresh issue-worktree session
verified clean local/remote `bc58022` and current `trunk` at `d19467d`, then
integrated that baseline, including accepted #17 / PR #19, #20 / PR #21 and
#18 / PR #22. The integration preserves the proposal, draft PR and review history,
adopts current BEHAVIOR session rules and retains this #3 return point.

The proposal and engineering appendix now retain the delivered source-owned YAML
`wsp` contract. The [authoring guide](../doc/authoring.md#local-workspaces) owns
workspace details. The candidate manifest uses `sources.aspirations` and the
`pfo/asp` default from accepted #15 / PR #16; other candidate selectors, identity
and definition fields remain proposed. Existing `pfo/okr` needs explicit selection.
No runtime changes beyond the integrated accepted baseline are introduced.

Next: discuss the smallest testable create/open and durable-definition slice.
Standard Act/Pfm, agent-assisted operation and one-way instance dependency remain
product directions; identity, persistence and public APIs still need agreement.
Publishing this draft does not approve implementation, migration, activation or
full view replacement. [#4](https://github.com/normenmueller/yap/issues/4) remains
separately scoped foundation work after the design decision. A continuation
supports this design discussion; it does not repeat the completed integration.

The owner also asks that #3 consider actual quip identification as a concrete
use case. [#8](https://github.com/normenmueller/yap/issues/8) owns collection scope;
the current `work_progress` scene uses explicitly illustrative data. Discuss what
constitutes one quip, its evidence and activity association, stable identity and
recognition on refresh before fixing relevant model/operation boundaries. This
note selects no evidence provider, changes no queue order and approves no collection.

The owner requests a concise PO-level recommendation on staying with Python or
switching to TypeScript/Haskell. Independent architecture, runtime and language
assessments recommend Python for the next product deliveries, including real
quip identification; the owner's technology decision remains pending. The existing
TypeScript proposal and #4 scope have not been accepted or rewritten by this advice.

<details>
<summary>Integration verification and review scope</summary>

All 283 existing tests passed on the integrated tree with PyYAML 6.0.3 in this
worktree's ignored virtual environment and local browser access. Runtime, assets,
tests and requirements match `d19467d`; only documentation/context differs from
that baseline. Markdown parsing, JSON examples, local file references and diff
whitespace checks pass. The first test attempt lacked PyYAML; the successful run
used the declared dependency. No separate full PDF/export review is claimed here.

Independent recovery review is pending completion of the merge. Complete it
before further substantive design changes. Earlier 254-test and synthetic
HTML/PDF/browser checks at `cf57907` apply only to that earlier baseline. Earlier
architecture review applies to its inspected proposal artifacts, not the current
reconciliation or future API/runtime changes. PR #14 remains a draft.

</details>

The application Project owns live status/order. Care references remain #12 and
README improvements #13; read their owning scope instead of duplicating a queue.
BEHAVIOR distinguishes design acceptance, implementation acceptance and merge
authority. No consumer revision or instance migration is selected here.
