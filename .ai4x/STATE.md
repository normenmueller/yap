# Return point — review the Python quality foundation

The owner selected Python as yap's application/domain core until further notice
and authorized a specialist development team, independent assessment and justified
code improvements. [TEAM.md](TEAM.md) owns the capabilities;
[python-quality.md](python-quality.md) owns the working method. Their scoped
independent review resolved its findings. This is application-development authority,
not accepted provider curation or instance care.

The selected work is [#3 / PR #14](https://github.com/normenmueller/yap/pull/14)
on `docs/3-architecture`. Next: support the owner's review of the delivered Python
quality changes. The owner remains requested as reviewer; no implementation
approval or merge has occurred. Follow BEHAVIOR's review/merge and session boundaries.
Do not start another backlog implementation or infer acceptance from these checks.

The change protects generated build/publication trees against preexisting symlinks,
hardlinks and special files, uses unique atomic text/publication writes, tightens
schema/date/preview/target decoding, removes unused PDF dependencies from `check`,
and reuses source catalogs safely. Cached navigation verifies collection roots and
fresh source hashes; private workspace values stay outside public models/caches.
Architecture/setup guidance now follows the accepted Python decision.

<details>
<summary>Verification, independent review and limits</summary>

All 312 tests passed on Python 3.15.2 with PyYAML 6.0.3 and local browser access.
The pinned mypy 2.4.0 gate passes strict checks for `outputs.py`, `source_values.py`
and a positive fixture; four invalid calls/assignments are rejected. The remaining
application modules are outside the strict gate. Python 3.10 syntax parsing passes;
other interpreter versions and Windows are not verified. The runtime uses POSIX.

A synthetic full report produced 25 site files including five PDFs. Extracted PDF
text, other generated files and model cache contained no private-workspace path or
target-content markers. Sources and target content were preserved, portable-export
SHA-256 inventories matched, and a repeated full build was up to date. The final
hardlink preflight also accepted that real renderer work/output tree.

On a synthetic 21-activity PipelineTests fixture, `resources` used 26 document
reads cold and zero warm (0.9806s/0.0368s in this local run). This is bounded command
and fixture evidence, not a general speed/scale or full-report one-pass claim.
Markdown, JSON examples, relative file references and whitespace checks pass.

Nonauthor source reviewers reproduced and rechecked the publication redirects,
cached collection-root bypass, cache/work hardlinks and preview calendar bound.
All actionable findings in the inspected change were resolved. Separate review
checked the architecture/setup records. No whole-codebase 10/10, concurrent-writer
exclusion, multi-instance service, full domain typing or owner acceptance is claimed.

</details>

The owner proposes closing the old #3/#4 TypeScript plan as not planned after
team/code preparation, then reassessing the backlog. Keep both open through the
current implementation review. Their surviving obligations are explicitly retained:
[#23](https://github.com/normenmueller/yap/issues/23) owns Python guided create/open,
stable portfolio identity and safe empty-instance construction;
[#24](https://github.com/normenmueller/yap/issues/24) owns remaining checked domain
boundaries and source/presentation separation; #12 owns durable Act/Pfm/local
definitions and care references. #23/#24 are Backlog, not Ready or delivered.
A future closure must explain the superseded language premise and these transfers,
not mark the missing product behavior completed.

Backlog assessment recommends refining real quip identification (#8) as the next
concrete product case, with the required typed boundaries, after this review and
closeout. The owner still controls selection/order. #5's pause, #6/#11 deferrals
and #13's hold remain effective; #7/#10 keep their separate effects/provider scopes.
The current quip scene remains illustrative. No evidence provider, collection
implementation, consumer revision, instance migration or activation is selected.
