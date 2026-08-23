# Adversarial divergence review — ARCHITECTURE-SPINE

**Verdict: not yet safe to decompose.** The spine has unusually strong artifact and
ownership rules, but the following underspecified seams permit two conscientious
teams to satisfy every adopted decision literally and still produce incompatible
or unrecoverable runs. These are contract holes, not requests to choose deferred
pilot values.

## Findings

### 1. Manifest publication has no predecessor/CAS rule, so a frozen-wave result can be lost

- **Location:** AD-3, AD-5, AD-9, AD-10; `UnitManifest` contract seed
- **Trigger condition:** Two workers in a frozen wave start from manifest `M0`.
  Worker A commits unit A and, while holding the run lock, atomically publishes
  `M1(A committed, B prepared)`. Worker B had already read `M0`; it subsequently
  acquires the lock and atomically publishes its valid `M2(A prepared, B
  committed)`. Both snapshots are valid, immutable, monotonic relative to the
  snapshot each worker read, and each publication obeys the one-writer lock.
- **Independently compliant implementations:** Team A makes every successor
  manifest carry and check its exact predecessor digest before replacing the ref.
  Team B treats the lock as sufficient and replaces the ref with a snapshot
  derived from its cached manifest. Neither behavior is forbidden or required by
  AD-3/9/10; B silently erases A from the current run state.
- **Potential consequence:** Resume sees a verified receipt for A but a manifest
  that no longer references it. A later retry can duplicate a paid model call,
  reintroduce an older result, or leave a completed unit apparently uncommitted.
- **Required guard:** Make `previous_manifest_digest` and an optimistic
  compare-and-swap of the run ref required kernel fields/operation. Define that a
  publisher must rebase disjoint unit advances inside the lock or reject and
  re-read on a predecessor mismatch; define the receipt-to-successor-manifest
  linkage.

### 2. Crash recovery lacks a durable invocation/idempotency protocol

- **Location:** AD-3, AD-6, AD-10, AD-11, AD-16; required-unit lifecycle
- **Trigger condition:** A live gateway call succeeds, but the process crashes
  after the provider receives it and before a Proposal object plus a terminal
  receipt are durably linked into a manifest. Resume is allowed to trust only
  verified receipts and referenced digests, yet there may be neither (or only an
  unlinked immutable object).
- **Independently compliant implementations:** Team A writes a `started` receipt
  with a stable logical invocation ID and sends that ID to the gateway/provider as
  an idempotency key; resume reconciles it. Team B writes receipts only at outcome
  and re-invokes after the crash, appending attempt 2. Both append attempts and
  never rewrite history, and both use the single gateway, but they cannot agree
  whether one logical proposal has been made or whether the second request is
  authorized.
- **Potential consequence:** duplicate live calls, divergent nondeterministic
  proposals for the same frozen context, exhausted budget accounting that differs
  by implementation, and no principled way to resume an interrupted attempt.
- **Required guard:** Specify an invocation state machine (`reserved`,
  `dispatched`, `provider-acknowledged`, `terminal`) with a durable logical
  invocation ID, request digest, gateway idempotency semantics, and a precise
  reconciliation/retry rule for every crash boundary. Bind attempt/budget ceilings
  to that logical invocation.

### 3. A “frozen context” is not itself a canonical, bound request contract

- **Location:** AD-5, AD-6, AD-11; `Proposal` provenance object
- **Trigger condition:** The same source unit has two committed earlier-wave
  target neighbors, a source neighbor, and a policy that permits them within a
  numeric bound. The spine does not define a canonical context-selection result,
  ordering/serialization, or require its digest in the proposal/gateway request.
- **Independently compliant implementations:** Team A freezes a per-unit
  `ContextBundle` ordered by source ordinal and includes both earlier target
  finals. Team B freezes a bundle ordered by commit time and includes the nearest
  target final that fits after a fixed prompt envelope. Both use only permitted
  earlier-wave artifacts, freeze before dispatch, respect the same ceilings, and
  record ordinary input artifact digests. They nonetheless submit different model
  requests under the same Unit Manifest and Context Policy identity.
- **Potential consequence:** retries and independent replays cannot establish
  which context generated a proposal; provider latency or implementation-local
  prompt budgeting leaks back into output differences despite AD-5's purpose.
- **Required guard:** Make Prepare (or a named deterministic kernel function)
  emit immutable, per-unit `ContextBundle` objects containing selected artifact
  digests, roles, canonical order, rendered-byte/request digest, truncation
  decision, and policy digest. Require the gateway and Proposal to reference the
  exact bundle digest.

### 4. Projection groups do not have a required mapping/selection contract across machine and human output

- **Location:** AD-12, AD-13, AD-15, AD-17, AD-19; `UnitManifest` and
  `UnitRecord` contract seed
- **Trigger condition:** A title Source Unit has a canonical title slot plus two
  declared navigation/title projections, then receives a valid Human Edit. The
  seed says only that a `UnitRecord` has a “projection group”; it does not require
  a projection-member schema with exact locators, a canonical-value selector for
  the reviewed export, or a binding from the selected Human Edit to all members.
- **Independently compliant implementations:** Team A represents the group as
  `{source_unit_id, member_locators[]}` and rebuilds every member from the export's
  selected value. Team B represents it as a group label on related UnitRecords and
  applies Human Edits only at the edited canonical slot, leaving generated title
  metadata/navigation values as their committed Machine Finals. Both keep Prepare
  as the only classifier/issuer of groups, only mutate declared projections, and
  can truthfully say Assembly projected one machine value to every declared
  projection. No AD states that reviewed export must re-project the selected edit.
- **Potential consequence:** reader title, navigation, and body disagree after
  review; different consumers can create incompatible draft/export HTML from the
  same immutable artifact set.
- **Required guard:** Define canonical `ProjectionGroup` and `ProjectionMember`
  kernel shapes (member typed locator, transformation/escaping rule, cardinality,
  canonical source unit, and ownership). Require every Assembly/ReviewedExport
  artifact to name the selected value digest and the exact projection-map digest,
  and validate all members against it.

### 5. Model Gateway verifies the envelope but not a canonical request or response provenance

- **Location:** AD-6, AD-11, AD-16; `Proposal` provenance object
- **Trigger condition:** A confirmed live package permits a model identity and
  ceilings. AD-11 says the gateway verifies those facts before resolving secrets,
  but it does not require a canonical gateway request schema/digest, decoding and
  tool parameters, provider routing/revision identity, or a gateway receipt that
  ties the response to that exact request.
- **Independently compliant implementations:** Team A's gateway rejects any
  caller lacking a request digest and pins `temperature`, `seed`, model revision,
  and system prompt from Translation Method. Team B accepts a source/binding-map
  request that is under the verified ceilings and lets the Run workflow choose a
  retry temperature and provider's moving model alias. Both make every live call
  through ModelGateway and verify method identity, context bounds, declaration,
  and secret eligibility exactly as AD-11 demands.
- **Potential consequence:** identical signed packages produce provenance that
  cannot show the actual model request or provider revision; evaluations and
  comparisons mix behaviorally different methods while claiming the same method
  identity.
- **Required guard:** Add a versioned canonical `ModelRequest`/`ModelResponse`
  contract: exact rendered inputs and bundle digest, model provider plus immutable
  revision/routing policy, all generation/tool parameters, idempotency key, and
  normalized response/usage digests. Require a gateway receipt and make Proposal
  reference both request and receipt digests; prohibit workflow-supplied settings
  outside the frozen Translation Method.

## Assessment

The holes cluster at handoff boundaries rather than within individual filters. A
small set of kernel contracts—manifest CAS lineage, invocation lifecycle,
context bundle, projection map, and gateway request/receipt—would make the
otherwise strong append-only design independently implementable.

## Post-fix verification

**PASS — all five previously reported divergence holes are closed at spine level.**

1. **Manifest loss:** AD-3 now requires predecessor digest, locked ref reread,
   compare-and-swap, deterministic disjoint rebase, and receipt-to-successor
   linkage. The stale-`M0` overwrite is no longer compliant.
2. **Crash/retry ambiguity:** AD-23 defines durable invocation receipt states,
   fixed request/idempotency identity, unknown-status reconciliation, and ceiling
   accounting. Auto-retrying an uncertain non-idempotent dispatch is prohibited.
3. **Context divergence:** AD-5 and the `ContextBundle` seed require a
   deterministic per-unit bundle, source-ordinal ordering, rendered bytes/digest,
   and Proposal/request references; implementation-local prompt selection is no
   longer compliant.
4. **Projection divergence:** AD-15 plus the `ProjectionMap` seed requires the
   selected-value and map digests and application to every member for reviewed
   export. The machine-only title/navigation alternative is excluded.
5. **Gateway provenance:** AD-11 and the `ModelRequest`/`ModelResponse` seed now
   bind immutable model revision, parameters, exact input, idempotency, response,
   usage, and a request-bound gateway receipt. Workflow-selected live settings or
   a moving alias are excluded.

No remaining high/critical hole was found in these five seams. The controls now
need contract-test enforcement during implementation; that is a verification
obligation, not a remaining architecture divergence.
