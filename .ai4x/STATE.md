# Return point — next architecture discussion

This is issue-linked `docs/3-architecture`, with the generic discussion proposal
for [#3 / PR #14](https://github.com/normenmueller/yap/pull/14). The owner is directly
requested as reviewer. [Proposal](../doc/architecture-proposal.md) owns future
choices; [engineering appendix](../doc/architecture-engineering.md) owns candidate
module/value/proof boundaries. [Current architecture](../doc/architecture.md)
owns delivered Python behavior. No private instance data or history is imported.

Current development focus: `docs/3-architecture`. `trunk` remains the accepted
Python application baseline. In the maintained checkout layout, the architecture
working copy is `docs/3-architecture` beside `trunk`; verify its actual location
with `git worktree list`. A fresh session opened in `trunk` should explain this
return point and direct the owner to the architecture working copy for this
discussion. Do not switch checkouts automatically or start implementation from
a status greeting. Explicit user tasks still take precedence.

Next: discuss the smallest testable create/open and durable-definition slice.
Standard Act/Pfm, agent-assisted operation and one-way instance dependency are
product directions; identity, persistence and public APIs still need agreement.
Publishing/rebasing this draft does not approve implementation, migration,
activation or full view replacement. [#4](https://github.com/normenmueller/yap/issues/4)
remains separately scoped foundation work after the design decision.

The owner approved the branding candidate at `6580d1d`; PR #2 is merged and #1 is
complete. This branch incorporates the accepted Python application and its
post-merge reviewer/recovery records. Runtime/resources/tests retain the approved
244-test implementation; this architecture proposal changes none of those bytes.
Earlier proposal/source review and its scoped recovery check remain evidence for
their inspected artifacts, not acceptance of future API or runtime changes.

The application Project owns live status/order. Care references remain #12 and
README improvements #13; read their owning scope instead of duplicating a queue.
BEHAVIOR requires requesting `normenmueller` on new managed PRs and distinguishes
review requests, design acceptance, implementation acceptance and merge authority.
