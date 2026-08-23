# Architecture Spine Rubric Review

**Target:** `ARCHITECTURE-SPINE.md`  
**Intent:** Validate; no spine changes made  
**Date:** 2026-08-23

## Gate verdict

**Needs revision before it is a safe build substrate for live work.** The spine is unusually strong on artifact identity, deterministic document handling, state separation, and the existing EPUB-reader ingress. Its mechanical contract is sound (`lint_spine.py`: 0 findings). However, it leaves two material PRD behaviors unbound and leaves the live operational trust/environment envelope too implicit. The deterministic-foundation slice can be scaffolded, but the gaps must be resolved before live-model or signing implementation proceeds.

## Evidence reviewed

- `ARCHITECTURE-SPINE.md`
- Literary Translation Suite `prd.md` and `addendum.md` (2026-08-23)
- Existing `src/epub-html/SKILL.md` and `src/epub-html/scripts/convert.py`
- Local runtime check: Python `3.14.4` and uv `0.11.19` are installed; the prospective i18n package/lockfile does not yet exist, and `pydantic` is not importable in the current workspace environment.

## Rubric results

| Rubric dimension | Result | Judgment |
| --- | --- | --- |
| Real divergence points | Partial | Core artifact, identity, state, token, and wavefront choices are real and well chosen. Live trust, editorial applicability, and candidate-role eligibility still permit incompatible implementations. |
| Enforceable AD rules | Partial | Most rules are testable, but AD-18 does not define what makes a signer trusted and the candidate/editorial requirements have no explicit rule to enforce. |
| Deferred safety | Partial | Pilot and method values are safely deferred behind gates. Key/signer trust, artifact-root operating model, and provider credential lifecycle are neither decided nor safely deferred. |
| Verified technology | Partial | Exact versions are named and Python/uv match the local host, but no lock or verification record establishes Pydantic/lxml availability, compatibility, or rationale for the new package. |
| Brownfield fit | Pass with watch item | AD-13 and AD-17 correctly recognize the existing reader as the upstream boundary and preserve its converter exemption. The new ownership/projection profile must be concretized from its real converter summary before Prepare is implemented. |
| Full capability coverage | Partial | The map cites every FR/NFR, but citations do not bind all consequential behavior: terminology/style applicability and Literal Anchor eligibility are not architecturally enforced. |
| Operational/environmental breadth | Fail | A filesystem diagram and run lock exist, but deployment/runtime ownership, artifact durability/retention, identity/key custody, credential source/rotation, and recovery expectations are silent. |

## Findings

### High — AD-18 does not establish a verifiable signing trust boundary

**Rubric:** real divergence points; enforceable rules; Deferred safety; operational breadth.  
**Evidence:** AD-18 requires a `PackageSigner` port, a detached signature, and a `signature identity`, while AD-11 resolves secrets after preflight. Neither rule says how a verifier maps that identity to trusted verification material, which algorithms/key identifiers are accepted, where key material is held, how rotation/revocation works, or what happens if verification infrastructure is unavailable.

Two independently implemented signer adapters can therefore both satisfy the prose while accepting different keys or treating an arbitrary local signing identity as trusted. This weakens the confirmation gate that protects FR-3, FR-26, and FR-28.

**Disposition:** Discuss and add an AD (or a tightly bounded Deferred item that blocks live mode) defining the trust store/authority, signer and verifier contract, key ID and rotation/revocation behavior, secret/key custody, and fail-closed behavior. This can deliberately remain provider-neutral.

### High — Editorial guidance and candidate-role eligibility are only mapped, not bound

**Rubric:** full capability coverage; enforceable rules.  
**Evidence:** FR-6 requires confirmed Terminology and Literary Style Sheets with unit applicability; FR-8 and FR-11–FR-14 require the Literal Anchor to be evaluator-only, only eligible candidates to be routed/committed, and every commitment to retain its evaluation path. AD-2/AD-6 make schemas possible and the capability map points to AD-5/AD-8/AD-10/AD-11, but none of their Rules makes those distinctions mandatory.

An implementation can conform to the present state machine and artifact convention while (a) treating a terminology sheet as unscoped prompt text, or (b) allowing a Literal Anchor or an unevaluated proposal to enter a `MachineFinal`. Those are explicitly prohibited PRD divergences.

**Disposition:** Autofix in an additional kernel/workflow AD: define frozen editorial artifacts and their Source Unit scopes as Run Snapshot inputs; define candidate kinds and the only transitions/eligibility that can produce `MachineFinal`; require a committed-final provenance link to an eligible evaluation and selection rationale.

### High — The filesystem-backed live operating model is incomplete

**Rubric:** operational/environmental breadth; Deferred safety; brownfield fit.  
**Evidence:** AD-3 and AD-9 specify atomic publication and a run lock, and the artifact-root sketch gives paths. The spine does not state supported runtime environments/filesystem semantics, artifact-root ownership and permissions, durability/backup/restore/retention policy, lock-loss/crash semantics, secret-reference provider and rotation, or how environment-specific adapter configuration is selected without becoming run truth.

For a local deterministic foundation this can be intentionally small; for live transfers and confirmation receipts it is a real compatibility and safety boundary. For example, a local NTFS artifact root and a synchronized/network directory may not share the same atomic-replace or locking guarantees.

**Disposition:** Add an MVP operational envelope AD, or explicitly defer each item with a condition that blocks live mode. At minimum bind the supported artifact-store filesystem class, single-host process model, permissions/owner model, publication/restore expectations, log/redaction behavior, and credential-reference lifecycle. Revisit distributed storage only when the existing AD-9 scale trigger is reached.

### Medium — Stack pins are not reproducibly verified in the brownfield workspace

**Rubric:** verified technology; brownfield fit.  
**Evidence:** AD-7/Stack pin Python 3.14.4, Pydantic 2.13.4, lxml 6.1.2, and uv 0.11.19. Local Python and uv agree with the pins, but there is no `src/i18n-pipeline/pyproject.toml` or `uv.lock` yet and Pydantic is not importable from the checked workspace. The reader converter currently supports a standard-library fallback and optional EbookLib/Beautiful Soup; it does not validate the future i18n lxml adapter.

This is not a reason to reject the chosen stack, but the spine presently presents prospective versions as already verified rather than as a reproducible package decision.

**Disposition:** Before implementation, create and lock the package with a compatibility/adapter-contract test against representative reader artifacts; record the verification source/date or move unverified package pins to a bounded implementation prerequisite. Do not alter the existing EPUB converter’s fallback contract unless separately approved.

## Positive controls retained

- AD-3 through AD-6 and AD-8 form a coherent, enforceable deterministic artifact model.
- AD-13, AD-17, and the canonical-source boundary generally ratify the existing `src/epub-html` ownership model rather than redesigning it.
- Pilot, method, and context numeric/content choices are deferred with explicit live-work gates, which is safe.
- The capability map is broad and provides a useful reconciliation index; the needed change is to turn the noted mapped capabilities into binding rules.

## Deterministic check

`uv run C:\\Users\\PaalA\\.codex\\skills\\bmad-architecture\\scripts\\lint_spine.py --workspace _bmad-output\\planning-artifacts\\architecture\\architecture-LibrarianLM-2026-08-23` completed with `ok: true` and zero findings.

## Post-fix verification

**Result: FAIL — one High finding remains.**

| Original finding | Verification | Result |
| --- | --- | --- |
| Signing trust boundary | AD-18 now fixes HMAC-SHA-256, an ACL-protected runtime key ring, key IDs/scheme versions, active/verify-only/revoked key behavior, and fail-closed verification. | Resolved |
| Editorial guidance and candidate eligibility | AD-21 freezes both editorial artifacts, resolves rules to Source Unit sets, makes Literal Anchors ineligible, and restricts `MachineFinal` to evaluated idiomatic/recovery candidates with provenance. | Resolved |
| Stack verification | AD-7 now makes `pyproject.toml`, `uv.lock`, lock digest, strict-input proof, and live startup identity checks an enforceable prerequisite rather than an unverified implementation assumption. | Resolved as a pre-implementation gate |
| Filesystem/live operating model | AD-22 materially fixes host/NTFS scope, permissions, credential references, lock reclaim, crash recovery, and startup checks. It does not decide or defer artifact retention/pruning and backup/restore. | **High remains** |

### High — Artifact retention and backup/restore are still unspecified

AD-22's durable-flush and receipt-chain recovery rules cover an interrupted local process, but do not state how immutable objects, receipts, manifests, and keys are retained, backed up, restored, or safely pruned. Independent implementations can therefore delete a still-referenced object, preserve different evidence windows, or restore an inconsistent object/ref set while still conforming to the declared NTFS envelope. This affects reproducibility, attribution, and recovery (FR-24; NFR-2–NFR-4).

**Required resolution:** add a compact live-mode rule that either retains the complete artifact/key set for the MVP and defines a verified restore procedure, or explicitly defers retention/pruning/backup while blocking live mode until those controls are set.

**Final verification: PASS.** AD-22 now prohibits automatic pruning/garbage collection, retains the complete object/receipt/ref/verify-key history, and makes backup/restore quiescent, empty-root, and fully verified before resume. No high or critical finding remains from this rubric review.
