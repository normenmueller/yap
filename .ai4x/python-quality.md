# Python design and quality contract

Develop yap as a semantically clear, modular, typed, robust and efficient Python
application. The owner's 10/10 ambition requires independent, scope-specific
evidence and resolved findings; it is not an unconditional score for every module
or a promise that static analysis proves correctness. Keep a lean implementation
and the accepted source contracts rather than pursuing stylistic churn.

## Design and typed boundaries

- Start with the source owner, invariant, input/output and effect boundary. Keep
  subject decisions independent of filesystem, browser and provider execution.
  Extract a module only when it owns a coherent responsibility or removes an
  actual dependency problem; avoid placeholder layers and universal frameworks.
- Use Python types to communicate and check real contracts. Prefer small immutable
  values, closed alternatives, precise collections and narrow protocols where
  their guarantees matter. A TypedDict describes a shape; it does not validate
  external data or prevent mutation. NewType distinguishes static identities; it
  does not establish runtime identity, existence or authority.
- Decode external JSON/YAML/process results at their owner, then validate subject
  and cross-source constraints. Check exact scalar kinds where Python's bool/int
  relationship matters. Checked construction owns its inputs; frozen containers
  must not retain externally mutable children when immutability is promised.
- Adopt a pinned static checker in meaningful bounded slices, with an explicit
  checked-file list and strict settings. Keep the unchecked remainder visible.
  Do not obtain a pass through blanket ignores, Any, unchecked casts or duplicate
  typed/untyped models. Compiler fixtures should demonstrate useful rejected
  calls as well as valid use. Runtime tests cover equivalent invalid external data.
- Share validated operations among CLI, agents and future browser clients. Keep
  browser interaction state distinct from facts; no synchronized second rule or
  source store. Preserve existing public contracts unless a change is agreed.

## Robustness and performance

- Test preservation before success: invalid input, redirected filesystem paths,
  stale plans and interrupted operations must not overwrite unrelated content.
  A preview is not execution authority; revision checks do not eliminate races
  with noncooperating external writers. State the guarantee actually achieved.
- Keep errors actionable and handle expected failures at the public boundary.
  Do not hide programming defects with broad catch-and-continue behavior. Preserve
  explicit uncertain outcomes for provider writes rather than blindly retrying.
- Find and measure hot paths with representative synthetic portfolios. Record
  fixture size, interpreter, command and cold/warm conditions for a performance
  claim. Prefer simpler algorithms and removal of repeated I/O before caching;
  cache invalidation must include every semantic input. No unmeasured speed claim.

## Independent assessment and delivery

1. Inspect the relevant existing behavior and source contracts. Report concrete
   findings and their impact; distinguish a reproducible defect, design debt and
   an unproven hypothesis. Preserve unrelated and private material.
2. Choose the smallest coherent remedy. Add discriminating regression checks for
   meaningful behavior and failure boundaries, not tests that repeat code shape.
3. Run the declared type gate and appropriate behavioral checks. Broaden testing
   only for relevant risk or unresolved findings; reuse valid unchanged evidence.
4. Have a nonauthor review semantics/types, module boundaries, preservation and
   failure behavior, verification and measured performance where applicable.
   Report remaining findings and coverage limits. A numeric assessment, if used,
   must identify its criteria and revision; no blanket 10/10 from a test count.
5. Give the owner a short account of changed behavior, evidence and remaining work.
   Keep engineering detail at the end. Separate design acceptance, implementation
   review and merge authority as defined in [BEHAVIOR.md](BEHAVIOR.md).

Record active decisions in STATE and issue-owned scope. Keep evidence in existing
tests, checks and engineering records; do not build a parallel review registry.
