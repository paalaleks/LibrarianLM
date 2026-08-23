---
title: '1.4 Preserve Inline Structure and Assemble Drafts'
type: 'feature'
created: '2026-08-23'
status: 'done'
review_loop_iteration: 1
baseline_commit: '01cf986e0bf06b3954be49a8bd9bacd676692b8c'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Prepared units cannot yet carry source-owned inline structure safely, and no assembly filter can place fixture target values into Canonical Source HTML without risking invented markup, lost bindings, or nondeterministic reconstruction.

**Approach:** Add a versioned protected-block fixture profile and immutable binding/segment artifacts, then assemble validated plain-text token streams into a secured lxml clone and emit a candidate draft plus canonical evidence.

## Boundaries & Constraints

**Always:** Work only under `src/i18n-pipeline`; Prepare alone owns segmentation, locations, projections, tokens, and maps. Use exact `[[[LLM:BIND:<26-character-base32-id>]]]` tokens derived from unit identity, kind, and source ordinal. Preserve the source artifact; resolve locations/fingerprints exactly; mutate only mapped Required slots in a clone. Keep fixture targets distinct from Machine Finals, order segments canonically, fan out only canonical projection values, and produce repeatable bytes.

**Ask First:** Adding dependencies; changing canonical serialization/Story 1.2 storage; accepting another projection transform; expanding markup or changing `src/epub-html`; weakening compatibility; or replacing the frozen slot profile.

**Never:** Parse targets as HTML; accept authored structure/IDs/locators; infer projections from equal text; use selectors, raw XPath, or fuzzy fallback; mutate nonmapped content; call a live gateway; perform Story 1.5 eligibility validation; or publish partial output after a blocker.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Inline round trip | Nested/movable inline nodes and valid tokens | Rebind one logical block with original node identity, attributes, order, and nesting | Missing, duplicate, invented, crossed, malformed, or foreign tokens block |
| Exact assembly | Complete matching source, manifest, maps, segments, and values | Change mapped clone slots once; preserve chrome, IDs, links, and footnotes | Missing values, drift, duplicate resolution, gaps, or unknown transforms return typed errors |
| Split/projection | Ordered block segments and a declared projection group | Segments rejoin by frozen ordinal and one canonical value is transformed onto every declared member | Conflicting member values, ordinal gaps/duplicates, or projection tampering block |
| Determinism | Identical frozen inputs | Candidate HTML and canonical artifacts are byte-equivalent | Report nondeterminism without a success claim |

</frozen-after-approval>

## Code Map

- `src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py:132,158,413,470,549,671,724` -- refine placement/binding invariants; require paired protected digests; validate exact entry order, kinds, pairs, singleton protected nodes, and segment/map correspondence; add fixture-target, candidate-draft, application-evidence, and result contracts.
- `src/i18n-pipeline/src/librarianlm_i18n/kernel/identity.py:67-96` -- reuse canonical digests and token rendering; add deterministic 26-character base32 token-ID derivation.
- `src/i18n-pipeline/src/librarianlm_i18n/ports/html_document.py:12-42` and `adapters/lxml_html_document.py:18-136` -- add clone, expected-fingerprint resolve/rebind, and serialization using existing child-axis/tail rules; preserve empty/void inline nodes and emit assemble-specific errors from assembly operations.
- `src/i18n-pipeline/src/librarianlm_i18n/ports/package_signer.py:27` -- inject the trusted verifier into Assembly and call `verify`; receipt/signature metadata equality alone is insufficient.
- `src/i18n-pipeline/src/librarianlm_i18n/workflows/prepare.py:50-151,202-239` -- persist protected-block segments/maps, recompute them during confirmation, and allow projected protected blocks only when member binding/segment topologies are isomorphic.
- `src/i18n-pipeline/src/librarianlm_i18n/workflows/assemble.py` -- cryptographically verify confirmation; require a complete/clean/ready manifest and exact canonical Required targets; validate map/segment correspondence; rebind projected members using deterministic member-token remapping; persist draft/report only on success.
- `src/i18n-pipeline/src/librarianlm_i18n/adapters/filesystem_artifact_store.py:219,233` -- reuse typed object storage unchanged. `src/epub-html/scripts/convert.py:346-447` is read-only preservation evidence.
- `src/i18n-pipeline/tests/{contracts/test_kernel.py,test_prepare.py,test_assemble.py}` -- extend current `unittest` fixtures and negative matrices, including forged signatures, protected structural drift/projections, empty/void inline nodes, incompatible persisted maps, blocked manifests, and unused targets; preserve the existing 49-test baseline.

## Tasks & Acceptance

**Execution:**
- [x] `kernel/{contracts.py,identity.py,__init__.py}` -- define digest domains and strict token, pair/singleton, nesting, segment-map, protected-digest, fixture, draft, placement, projection, and report contracts.
- [x] `ports/html_document.py`, `ports/package_signer.py`, `adapters/lxml_html_document.py`, and exports -- add fail-closed clone/resolve/rebind/serialize operations that never consume target markup and require trusted signature verification.
- [x] `workflows/prepare.py` -- add protected-block preparation while retaining slot-only compatibility; persist/recompute maps and segments; include empty/void inline bindings; reject non-isomorphic protected projection members.
- [x] `workflows/assemble.py` and `workflows/__init__.py` -- verify the HMAC signature and manifest readiness, reject noncanonical/unused targets, validate artifact correspondence, remap protected projections per member, publish immutable outputs, and return deterministic actionable failures.
- [x] `tests/` -- cover nested/moved/empty/void bindings, text/tails/attributes, split blocks, plain and protected projections, source/protected-fingerprint drift, forged signatures, malformed/foreign/inconsistent tokens, blocked manifests, unused targets, preservation, unsupported transforms, and byte equivalence.

**Acceptance Criteria:**
- Given a supported protected block, when Prepare confirms it, then every inline boundary/value has one token/map entry, each Required unit references persisted maps/segments, and recomputation rejects drift.
- Given valid fixture targets and a confirmed graph, when Assembly runs, then each Required canonical unit applies once to a clone, projections receive its value, and structure/nonmapped content remain unchanged.
- Given any invalid token, placement, lineage, projection, or structural resolution, when Assembly validates inputs, then it emits ordered blocking evidence and publishes neither candidate draft nor successful report.
- Given identical frozen inputs, when dummy round trips and Assembly repeat, then selection, placement, splits, projections, anchors, footnotes, HTML, and report bytes are equivalent.

## Spec Change Log

- Iteration 1 — Review found that Assembly could trust forged signature metadata and had no valid rule for projecting a protected canonical token stream onto members with unit-specific tokens; persisted binding/segment contracts also allowed inconsistent pairs, empty-node loss, and protected-fingerprint bypass. Amended the Code Map, tasks, tests, and design notes to require trusted `PackageSigner.verify`, ready-manifest/exact-target gates, strict map/segment correspondence, singleton empty/void bindings, expected-fingerprint rebinding, and isomorphic member-token remapping. This avoids authorizing unconfirmed graphs or publishing projections with literal tokens, stale inline text, or drifted placement. KEEP: exact ASCII tokens, fixture targets distinct from Machine Finals, Prepare-owned segmentation/maps, clone-only lxml mutation, escaped target markup, deterministic canonical artifacts, declared-only projections, source/chrome/anchor/footnote preservation, and the successful negative/determinism test approach.

## Design Notes

The protected-block profile is a new segmentation version. Slot-only fixtures remain valid without bindable inline structure; incompatible inline input becomes Unsupported. Map digests cover unit/source identity and entries, excluding the digest field. Paired containers and singleton empty/void nodes must each appear exactly once; pairs may move only inside their unit while balanced, nested, and non-crossing. Segment-map tokens must exactly equal binding-map tokens and preserve canonical ordinals. Protected projection members must have isomorphic kind/pair/segment topology; Assembly maps canonical token positions to each member's unit-derived token IDs before rebinding, or fails closed. Assembly receives a trusted `PackageSigner`, verifies the detached HMAC, checks complete/clean/ready status, and rejects any supplied target outside the canonical Required inventory. Missing-ID diagnostics are source-order deterministic, and rebind compares the manifest's stored fingerprint rather than a freshly accepted value. Story 1.5 alone decides draft eligibility/compliance.

## Verification

**Commands:**
- `uv --version` -- expected: exactly `uv 0.11.19`.
- `uv sync --locked --python 3.14.4` from `src/i18n-pipeline` -- expected: no lockfile change.
- `uv run --frozen python -m unittest discover -s tests -p "test_*.py"` from `src/i18n-pipeline` -- expected: all existing and Story 1.4 tests pass.
- `uv run --frozen python -c "import librarianlm_i18n; import librarianlm_i18n.workflows; import librarianlm_i18n.ports; import librarianlm_i18n.adapters"` from `src/i18n-pipeline` -- expected: public surfaces import successfully.

## Suggested Review Order

**Confirmed assembly boundary**

- Start with the trust, inventory, mutation, projection, and publication sequence.
  [`assemble.py:37`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/assemble.py#L37)

- Follow protected-artifact lineage and source-integrity enforcement before mutation.
  [`assemble.py:117`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/assemble.py#L117)

- Inspect member-specific token remapping for protected projection fan-out.
  [`assemble.py:137`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/assemble.py#L137)

**Protected DOM reconstruction**

- See how Prepare converts supported inline structure into source-owned bindings.
  [`lxml_html_document.py:66`](../../src/i18n-pipeline/src/librarianlm_i18n/adapters/lxml_html_document.py#L66)

- Review validated mixed-content reconstruction and legal physical inline movement.
  [`lxml_html_document.py:113`](../../src/i18n-pipeline/src/librarianlm_i18n/adapters/lxml_html_document.py#L113)

- Confirm plain slots remain escaped text-only mutations.
  [`lxml_html_document.py:146`](../../src/i18n-pipeline/src/librarianlm_i18n/adapters/lxml_html_document.py#L146)

**Preparation and contracts**

- Trace protected artifacts from stable Source Unit identity into the manifest.
  [`prepare.py:217`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/prepare.py#L217)

- Check declared projection compatibility and isomorphic protected topology.
  [`prepare.py:236`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/prepare.py#L236)

- Review strict token derivation, pair balance, and canonical map integrity.
  [`contracts.py:432`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py#L432)

- Finish contract review with segment, evidence, report, and result bindings.
  [`contracts.py:489`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py#L489)

**Verification evidence**

- Begin with deterministic protected projection and singleton round trips.
  [`test_assemble.py:75`](../../src/i18n-pipeline/tests/test_assemble.py#L75)

- Audit signature and invalid-token failures that publish no draft.
  [`test_assemble.py:88`](../../src/i18n-pipeline/tests/test_assemble.py#L88)

- Verify readiness, lineage, fingerprint, and persisted-artifact tamper gates.
  [`test_assemble.py:120`](../../src/i18n-pipeline/tests/test_assemble.py#L120)

- End with movement, selection, identity, escaping, and projection-order regressions.
  [`test_assemble.py:184`](../../src/i18n-pipeline/tests/test_assemble.py#L184)
