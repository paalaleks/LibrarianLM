---
title: '1.3 Prepare Stable Source Units'
type: 'feature'
created: '2026-08-23'
status: 'done'
review_loop_iteration: 2
baseline_commit: '98523ad7768dd70e980897566c9c3474d23ad955'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Later translation stages lack an authoritative, reproducible scope tying every book-owned location to its source, eligibility, structure, projection membership, and confirmed editorial rules.

**Approach:** Add a fixture-mode Prepare workflow that validates a Canonical Source Package, securely parses its HTML, deterministically classifies and segments book-owned locations, publishes a frozen unit inventory, and gates confirmation with a detached HMAC signature and separate operator receipt.

## Boundaries & Constraints

**Always:** Keep code under `src/i18n-pipeline`; use strict frozen versioned contracts, canonical bytes, typed actionable errors, and the Story 1.2 store. Prepare alone owns classification, segmentation, order, structured locators, and complete projection maps. Represent every selected book-owned location as Required, Excluded, or Unsupported; only Required entries are translation work, Excluded values remain exact round-trip inputs, and any unresolved Unsupported entry or empty Required set blocks signing. Derive each ID once from Canonical Source HTML digest, owned-root/path/text-slot identity, segmentation-profile version, and segment ordinal; keep exact source-text digest separate and fail terminally on attempted identity reuse with changed text. Treat nonzero aggregate-only book-owned omissions as blocking evidence. Resolve confirmed terminology/style rules to explicit existing Required unit IDs; explicitly empty confirmed sheets are valid. Keep signatures detached from canonical package content and secrets outside artifacts.

**Ask First:** Adding dependencies; changing canonical serialization or Story 1.2 persistence semantics; weakening fail-closed omission, identity, compatibility, or signature rules; supporting live model calls or production secret storage; expanding supported markup beyond the frozen fixture preparation policy.

**Never:** Persist CSS selectors or raw XPath as locators; translate chrome, controls, CSS, JavaScript, generated facts, or duplicate projections independently; silently drop ambiguous content, resegment downstream, include timestamps/paths/secrets in deterministic artifacts, invent HTML, or implement Story 1.4 inline binding/assembly or Story 1.6 public orchestration.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Deterministic prepare | Valid package, zero blocking omissions, supported book content, confirmed sheets | Byte-equivalent ordered units/manifest/projections and `ready-for-confirmation` package across repeated runs | No live gateway resolution; canonical outputs are identical |
| Ownership and eligibility | Book content mixed with application chrome, duplicates, exclusions, and ambiguous markup | Chrome is outside selection; duplicates share one canonical unit; every selected location is classified; excluded source is retained | Unsupported or no Required units emits blocked findings and no signature |
| Identity integrity | Prior unit locator/profile identity is presented with changed exact source text | No old ID is reused and no downstream artifact is published as ready | Terminal `source-text-digest-mismatch` with restart guidance |
| Confirmation trust | Valid package and scoped sheets with active key, or unknown/revoked/mismatched key | Detached HMAC-SHA-256 signature plus separate operator receipt only after verification | Missing/untrusted/unavailable verification fails closed |

</frozen-after-approval>

## Code Map

- `src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py:74` -- reuse strict contract base; refine locator/unit shapes and add digest-bound ownership/projection/segmentation profiles, structural fingerprints, source/package, editorial, signature, confirmation, and preparation-outcome contracts.
- `src/i18n-pipeline/src/librarianlm_i18n/kernel/{identity.py:67,boundary.py:71,errors.py:15,canonical.py:85}` -- reuse exact text hashing, canonical typed IDs, hostile-input gates, and actionable failures.
- `src/i18n-pipeline/src/librarianlm_i18n/kernel/__init__.py:1` -- expose the authoritative preparation contract surface.
- `src/i18n-pipeline/src/librarianlm_i18n/workflows/prepare.py` -- deterministic classification, fixture-v1 slot segmentation, declared-projection assembly, outcome publication, and confirmation; confirmation must recompute the entire inventory from the persisted source/profile/policy graph.
- `src/i18n-pipeline/src/librarianlm_i18n/ports/{html_document.py,package_signer.py}` -- new parser/document and signer boundaries; signer API never exposes key material.
- `src/i18n-pipeline/src/librarianlm_i18n/adapters/{lxml_html_document.py,hmac_package_signer.py}` -- secured strict lxml implementation with inherited ownership dispositions and unique roots, plus an exception-safe stdlib HMAC key-ring adapter.
- `src/i18n-pipeline/src/librarianlm_i18n/adapters/filesystem_artifact_store.py:618` -- reuse immutable object publication, manifest CAS, outcome receipts, and verified recovery; do not change storage protocol.
- `src/epub-html/scripts/{convert.py:554,template.html:593}` -- read-only ownership/projection evidence for fixture classification; do not couple packages by importing converter code.
- `src/i18n-pipeline/tests/` -- update kernel/store fixtures and add contract, lxml adapter, signer, and Prepare workflow matrices using existing `unittest` conventions.

## Tasks & Acceptance

**Execution:**
- [x] `src/i18n-pipeline/src/librarianlm_i18n/kernel/{contracts.py,identity.py,__init__.py}` -- define the complete strict preparation graph, including embedded/digest-bound compatible profiles, structural fingerprints, declared projections, unique terminology/style sheets, findings/outcomes, and unambiguous IDs.
- [x] `src/i18n-pipeline/src/librarianlm_i18n/ports/` and `src/i18n-pipeline/src/librarianlm_i18n/adapters/` -- add strict HTML/HMAC boundaries; require durable unique owned-root IDs, classify tails by their parent, prevent Required overrides beneath Excluded/Unsupported ancestors, honor application-owned markers, reject parser-repaired structure, and select every profile-declared book-owned attribute.
- [x] `src/i18n-pipeline/src/librarianlm_i18n/workflows/prepare.py` -- validate profiles/findings before parsing; apply explicit fixture-v1 one-unit-per-nonblank-slot segmentation; create groups only from declared projection keys/members; keep changed profile domains independent during prior checks; publish blocked outcomes; and confirm only after recomputing byte-equivalent locations, fingerprints, units, projections, manifest, policy, and sheets from the persisted graph.
- [x] `src/i18n-pipeline/tests/` -- cover every matrix row and prior iteration cases plus real text/tail/attribute extraction, tail ownership, nested Required override rejection, idless roots, application-owned descendants, profile incompatibility, structural drift, equal-but-unprojected text, declared projection tampering, profile-version changes, signed findings, unique sheet kinds, and blocked-outcome history.

**Acceptance Criteria:**
- Given a compatible Canonical Source Package, when Prepare runs, then every required component is digest-bound before secured lxml parsing and upstream book-owned omissions block with actionable findings.
- Given mixed reader HTML, when eligibility completes, then stable typed locations and complete projection groups preserve all selected book-owned values while excluding application-owned material from translation.
- Given identical frozen inputs, when Prepare repeats, then its ordered unit, manifest, projection, sheet, and package artifacts are byte-equivalent and contain no operational metadata.
- Given confirmed editorial scopes and a trusted signing key, when the operator confirms, then all scopes resolve to explicit Required units and a verified detached signature plus separate confirmation receipt gates downstream use.
- Given any direct or malformed confirmation input, when confirmation runs, then it reloads the digest-addressed prepared package and referenced artifacts, verifies readiness and confirmed sheets plus requested/signature key equality, and converts invalid types, missing objects, revoked keys, and tampering into actionable failures.
- Given persisted but fabricated or drifted preparation artifacts, when confirmation recomputes from the bound source and profiles, then any byte-level difference in locations, fingerprints, units, projections, findings, policy, sheets, or manifest blocks signing.

## Spec Change Log

- Iteration 1 — Review found that classification/profile semantics and the confirmation trust boundary were underspecified, permitting ignored/inherited exclusions, dropped converter findings, projection-incompatible grouping, repaired malformed HTML, prior-ordinal mismatch evasion, and signing of fabricated or unconfirmed packages. Amended the Code Map, tasks, acceptance, and design notes to require strict inherited classification, unique roots, full finding evaluation, compatible projections, persisted-ordinal integrity, store-reloaded confirmation, key binding, exception safety, and focused negative tests. This avoids publishing or certifying an inventory that bypassed Prepare. KEEP: strict frozen contracts, selector-free locators, deterministic digest-derived identities, Story 1.2 artifact publication, detached HMAC signatures/receipts, and the original deterministic/blocking/trust test matrix.
- Iteration 2 — Review found that profiles were unenforced IDs, equal text was mistaken for projection evidence, fingerprints and explicit segmentation behavior were absent, tail/application ownership could be misclassified, and confirmation validated graph coherence without deterministic re-preparation. Amended contracts, adapter/workflow tasks, acceptance, and design notes to require embedded compatible profiles, declared projections only, structural fingerprints, explicit slot segmentation, parent-owned tails, durable roots, application-owned exclusions, full recomputation before signing, signed findings, and blocked outcome receipts. This avoids stable-looking packages whose inventory was inferred, repaired, drifted, or fabricated. KEEP: all Iteration 1 constraints plus store-backed confirmation, inherited classification, strict structure probing, identity-input separation, signer exception safety, and the expanded 45-test negative matrix.

## Design Notes

Story 1.3 refines the pre-release v1 `TypedLocator`/`UnitRecord` contract rather than introducing selector-shaped parallel contracts; all existing fixtures migrate together. Unit records cover selected nonblank book-owned value slots across all eligibility states, while only Required records enter translation work; blank slots are retained structurally by the immutable source package rather than becoming units. Ancestor and configured profile dispositions inherit to descendants, owned-root IDs must be unique, and projection members must share eligibility, content class, and transformation semantics. `inline_binding_map_digest` remains null until Story 1.4.

Fixture-v1 segmentation is deliberately one Source Unit per nonblank profile-selected text, parent-owned tail, or book-owned attribute slot; this is a real versioned rule, not implicit adapter behavior. A required descendant cannot override an Excluded/Unsupported ancestor. Owned roots require durable unique IDs. The source package embeds versioned ownership and projection profiles (or immutable digest references resolved before parsing); policy compatibility is exact. Projection groups come only from declared profile evidence such as an approved projection key and never from equal text. Each location/unit carries a deterministic structural fingerprint over owned-root/path/slot plus stable element shape.

The canonical Prepare Package contains digest references to the source package, frozen run snapshot, manifest, policy, component identities, exactly one confirmed terminology sheet, exactly one confirmed style sheet (each may have zero rules), findings, and the profiles they use. Its detached signature covers that package digest; operator/time/key binding lives in a separate receipt, and no mutable `CONFIRMED` package is created. Confirmation accepts a digest, reloads the published graph, reruns selection/classification/segmentation/projection construction from the stored source and profiles, compares canonical bytes for every derived artifact, and checks requested-key equality before writing signature/receipt. Blocked attempts append an operational outcome rather than masquerading as published preparation. A prior manifest is only an integrity guard and is compared only inside the same segmentation-profile domain using final persisted ordinals.

## Verification

**Commands:**
- `uv --version` -- expected: exactly `uv 0.11.19`.
- `uv sync --locked --python 3.14.4` -- expected: locked environment installs without lockfile changes.
- `uv run --frozen python -m unittest discover -s tests -p "test_*.py"` from `src/i18n-pipeline` -- expected: all kernel, persistence, adapter, signer, and Prepare tests pass.
- `uv run --frozen python -c "import librarianlm_i18n; import librarianlm_i18n.workflows; import librarianlm_i18n.ports; import librarianlm_i18n.adapters"` from `src/i18n-pipeline` -- expected: authoritative package surfaces import successfully.

## Suggested Review Order

**Preparation and confirmation flow**

- Start with deterministic preparation, persistence, and outcome publication.
  [`prepare.py:50`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/prepare.py#L50)

- Review store-backed recomputation before any package receives a signature.
  [`prepare.py:103`](../../src/i18n-pipeline/src/librarianlm_i18n/workflows/prepare.py#L103)

**HTML ownership and structure**

- Inspect the fail-closed lxml entry boundary and repair detection.
  [`lxml_html_document.py:21`](../../src/i18n-pipeline/src/librarianlm_i18n/adapters/lxml_html_document.py#L21)

- Follow inherited eligibility, parent-owned tails, attributes, and fingerprints.
  [`lxml_html_document.py:82`](../../src/i18n-pipeline/src/librarianlm_i18n/adapters/lxml_html_document.py#L82)

**Contracts and trust**

- See how source HTML binds ownership, projection, and segmentation profiles.
  [`contracts.py:278`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py#L278)

- Check exact policy compatibility and signed package digest bindings.
  [`contracts.py:297`](../../src/i18n-pipeline/src/librarianlm_i18n/kernel/contracts.py#L297)

- Review detached HMAC key trust and verification behavior.
  [`hmac_package_signer.py:16`](../../src/i18n-pipeline/src/librarianlm_i18n/adapters/hmac_package_signer.py#L16)

**Verification evidence**

- Confirm deterministic projection behavior and byte-equivalent repeated preparation.
  [`test_prepare.py:121`](../../src/i18n-pipeline/tests/test_prepare.py#L121)

- Verify warnings remain signed while disallowed findings block publication.
  [`test_prepare.py:176`](../../src/i18n-pipeline/tests/test_prepare.py#L176)

- Finish with recomputation, drift rejection, signing, and confirmation receipts.
  [`test_prepare.py:213`](../../src/i18n-pipeline/tests/test_prepare.py#L213)
