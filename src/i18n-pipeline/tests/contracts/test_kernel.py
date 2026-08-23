from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from pydantic import ValidationError

from librarianlm_i18n import kernel
from librarianlm_i18n.kernel.contracts import (
    ArtifactReference,
    CompatibilityMetadata,
    ContentClass,
    ContextArtifact,
    ContextBundle,
    ContextRole,
    Eligibility,
    ProjectionMap,
    ProjectionOwnership,
    StatusValue,
    StatusVector,
    TypedLocator,
    UnitManifest,
    UnitRecord,
)
from librarianlm_i18n.kernel.errors import actionable_error


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
UNIT_ID = f"source-unit:{DIGEST_A}"
GROUP_ID = f"projection-group:{DIGEST_B}"
TOKEN_ID = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def locator() -> TypedLocator:
    return TypedLocator(locator="dom:body/p[1]", kind="text")


def statuses(**changes: StatusValue) -> StatusVector:
    fields = {
        "processing": StatusValue.NOT_STARTED,
        "completeness": StatusValue.UNKNOWN,
        "compliance": StatusValue.UNKNOWN,
        "review": StatusValue.NOT_STARTED,
        "publication": StatusValue.NOT_READY,
    }
    fields.update(changes)
    return StatusVector(**fields)


def valid_manifest() -> UnitManifest:
    unit = UnitRecord(
        source_unit_id=UNIT_ID,
        ordinal=0,
        locator=locator(),
        source_digest=DIGEST_A,
        content_class=ContentClass.TEXT,
        eligibility=Eligibility.REQUIRED,
        eligibility_reason="translatable text",
        projection_group_id=GROUP_ID,
        lifecycle_state=kernel.UnitLifecycleState.PREPARED,
    )
    projection = ProjectionMap(
        group_id=GROUP_ID,
        canonical_source_unit_id=UNIT_ID,
        member_locators=(locator(),),
        ownership=ProjectionOwnership.WORKFLOW,
        cardinality=1,
        transformation_rule="replace-text",
    )
    return UnitManifest(
        source_package_digest=DIGEST_A,
        run_snapshot_digest=DIGEST_B,
        segmentation_profile_id="component:segmenter-v1",
        profile_id="component:profile-v1",
        units=(unit,),
        projection_groups=(projection,),
        status=statuses(),
        provenance=(),
    )


def context_artifact(ordinal: int, role: ContextRole = ContextRole.SOURCE) -> ContextArtifact:
    return ContextArtifact(
        role=role,
        source_order_ordinal=ordinal,
        reference=ArtifactReference(kind="fixture", digest=DIGEST_A),
        rendered_fragment="fixture",
    )


class KernelContractTests(unittest.TestCase):
    def test_project_toolchain_pins_are_exact(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with (project_root / "pyproject.toml").open("rb") as source:
            pyproject = tomllib.load(source)
        self.assertEqual(pyproject["project"]["requires-python"], "==3.14.4")
        self.assertEqual(
            set(pyproject["project"]["dependencies"]),
            {"pydantic==2.13.4", "lxml==6.1.2"},
        )
        self.assertEqual(pyproject["tool"]["uv"]["required-version"], "==0.11.19")

    def test_inventory_exposes_one_contract_family(self) -> None:
        required = (
            "UnitManifest",
            "UnitRecord",
            "InlineBindingMap",
            "ContextBundle",
            "ProjectionMap",
            "ModelRequest",
            "ModelResponse",
            "ComponentIdentity",
            "AssemblyReport",
            "ValidationReport",
            "TranslationRunSummary",
            "RunComparison",
            "UsefulnessEvaluationReport",
            "Proposal",
            "Evaluation",
            "RecoveryCandidate",
            "MachineFinal",
            "FailedUnit",
            "HumanEditSet",
            "BookFinding",
            "GatewayReceipt",
        )
        for name in required:
            self.assertTrue(hasattr(kernel, name), name)
        self.assertEqual(type(valid_manifest().units), tuple)
        with self.assertRaises(ValidationError):
            valid_manifest().schema_version = 2

    def test_typed_identity_is_digest_derived_and_not_path_based(self) -> None:
        identity = kernel.derive_typed_id("source-unit", {"ordinal": 0, "source": DIGEST_A})
        self.assertTrue(identity.startswith("source-unit:"))
        self.assertEqual(len(identity), len("source-unit:") + 64)
        self.assertEqual(kernel.source_text_digest("same"), kernel.source_text_digest("same"))
        with self.assertRaises(ValueError):
            kernel.derive_typed_id("Source Unit", {})

    def test_inline_binding_ids_and_rendering_are_exact(self) -> None:
        self.assertEqual(kernel.render_protected_token(TOKEN_ID), "[[[LLM:BIND:ABCDEFGHIJKLMNOPQRSTUVWXYZ]]]")
        entry = kernel.TokenEntry(
            token_id=TOKEN_ID,
            kind="emphasis",
            source_order_ordinal=0,
            locator=locator(),
            source_node="em",
            placement_rule="inline",
        )
        self.assertEqual(entry.token_id, TOKEN_ID)
        for invalid in ("token:" + DIGEST_A, "abcdefghijklmnopqrstuvwxy2", "A" * 25, "A" * 27):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                entry.model_copy(update={"token_id": invalid}).__class__(
                    **(entry.model_dump() | {"token_id": invalid})
                )
        with self.assertRaises(ValueError):
            kernel.render_protected_token("a" * 26)

    def test_canonical_bytes_are_repeatable_utf8_lf_and_compact(self) -> None:
        artifact = ArtifactReference(kind="fixture", digest=DIGEST_A)
        first = kernel.canonical_bytes(artifact)
        self.assertEqual(first, kernel.canonical_bytes(artifact))
        self.assertEqual(first, b'{"digest":"' + b"a" * 64 + b'","kind":"fixture","schema_version":1}\n')
        self.assertFalse(b": " in first)
        with self.assertRaises(TypeError):
            kernel.canonical_bytes({"score": 0.5})

    def test_status_dimensions_are_independent(self) -> None:
        vector = statuses(processing=StatusValue.COMPLETE, compliance=StatusValue.FAILED)
        self.assertEqual(vector.processing, StatusValue.COMPLETE)
        self.assertEqual(vector.compliance, StatusValue.FAILED)
        self.assertEqual(vector.publication, StatusValue.NOT_READY)

    def test_contract_inventory_invariants(self) -> None:
        base = valid_manifest()
        unit = base.units[0]
        for eligibility in Eligibility:
            with self.subTest(eligibility=eligibility), self.assertRaises(ValidationError):
                UnitRecord(
                    **(unit.model_dump() | {"eligibility": eligibility, "eligibility_reason": ""})
                )
            with self.subTest(eligibility=eligibility, reason="whitespace"), self.assertRaises(ValidationError):
                UnitRecord(
                    **(unit.model_dump() | {"eligibility": eligibility, "eligibility_reason": " "})
                )
        projection = base.projection_groups[0]
        with self.assertRaises(ValidationError):
            ProjectionMap(**(projection.model_dump() | {"cardinality": 2}))
        with self.assertRaises(ValidationError):
            ProjectionMap(**(projection.model_dump() | {"member_locators": (), "cardinality": 0}))

        second = UnitRecord(
            **(
                unit.model_dump()
                | {
                    "source_unit_id": f"source-unit:{DIGEST_B}",
                    "ordinal": 1,
                }
            )
        )
        with self.assertRaises(ValidationError):
            UnitManifest(**(base.model_dump() | {"units": (second, unit)}))
        with self.assertRaises(ValidationError):
            UnitManifest(**(base.model_dump() | {"units": (unit, unit)}))
        duplicate_group = ProjectionMap(
            **(projection.model_dump() | {"canonical_source_unit_id": second.source_unit_id})
        )
        with self.assertRaises(ValidationError):
            UnitManifest(**(base.model_dump() | {"units": (unit, second), "projection_groups": (projection, duplicate_group)}))
        missing_group = ProjectionMap(
            **(projection.model_dump() | {"canonical_source_unit_id": second.source_unit_id})
        ).model_copy(update={"group_id": f"projection-group:{DIGEST_A}"})
        with self.assertRaises(ValidationError):
            UnitManifest(**(base.model_dump() | {"projection_groups": (missing_group,)}))
        unresolved = unit.model_copy(update={"projection_group_id": f"projection-group:{DIGEST_A}"})
        with self.assertRaises(ValidationError):
            UnitManifest(**(base.model_dump() | {"units": (unresolved,)}))

    def test_context_artifacts_are_typed_and_source_ordered(self) -> None:
        bundle = ContextBundle(
            source_unit_id=UNIT_ID,
            policy_digest=DIGEST_A,
            artifacts=(context_artifact(0), context_artifact(0, ContextRole.TARGET), context_artifact(1)),
            token_budget=0,
            decisions=(),
            rendered_bytes_digest=DIGEST_B,
        )
        self.assertEqual(bundle.artifacts[1].role, ContextRole.TARGET)
        with self.assertRaises(ValidationError):
            ContextBundle(**(bundle.model_dump() | {"artifacts": (context_artifact(1), context_artifact(0))}))


class BoundaryTests(unittest.TestCase):
    def test_hostile_json_matrix_is_rejected_before_feature_logic(self) -> None:
        good = valid_manifest().model_dump_json()
        cases = (
            ('duplicate', '{"schema_version":1,"schema_version":1}', "malformed-artifact", "hostile-json"),
            ('unknown', good[:-1] + ',"unexpected":true}', "malformed-artifact", "strict-schema"),
            ('coercion', good.replace('"ordinal":0', '"ordinal":"0"'), "malformed-artifact", "strict-schema"),
            ('float', good.replace('"ordinal":0', '"ordinal":0.0'), "malformed-artifact", "hostile-json"),
            ('nan', good.replace('"ordinal":0', '"ordinal":NaN'), "malformed-artifact", "hostile-json"),
            ('stale-root', good.replace('"schema_version":1', '"schema_version":2'), "incompatible-artifact-version", "accepted-schema-version"),
            ('stale-child', good.replace('"schema_version":1,"source_unit_id"', '"schema_version":2,"source_unit_id"'), "incompatible-artifact-version", "accepted-schema-version"),
        )
        for name, raw, code, rule in cases:
            with self.subTest(name=name):
                called = False

                def feature(_: UnitManifest) -> str:
                    nonlocal called
                    called = True
                    return "must not run"

                result = kernel.run_boundary(raw, UnitManifest, feature, workflow="prepare")
                self.assertIsNone(result.value)
                self.assertIsNotNone(result.error)
                self.assertFalse(called)
                self.assertEqual(result.error.code, code)
                self.assertEqual(result.error.rule, rule)
                self.assertEqual(result.error.workflow, "prepare")
                self.assertEqual(result.error.subject, "artifact")
                self.assertEqual(result.error.retryability, kernel.Retryability.NOT_RETRYABLE)
                self.assertTrue(result.error.expected)
                self.assertTrue(result.error.observed)
                self.assertTrue(result.error.next_action)

    def test_valid_boundary_invokes_feature_once(self) -> None:
        calls = 0

        def feature(value: UnitManifest) -> str:
            nonlocal calls
            calls += 1
            return value.source_package_digest

        result = kernel.run_boundary(
            valid_manifest().model_dump_json(), UnitManifest, feature, workflow="prepare"
        )
        self.assertEqual(result.value, DIGEST_A)
        self.assertIsNone(result.error)
        self.assertEqual(calls, 1)

    def test_compatibility_and_source_text_mismatch_are_stable_failures(self) -> None:
        metadata = CompatibilityMetadata(contract_name="unit-manifest", accepted_versions=(1,))
        missing = kernel.validate_boundary(None, UnitManifest, workflow="prepare")
        self.assertEqual(missing.error.code, "missing-artifact")
        stale = valid_manifest().model_copy(update={"schema_version": 2}).model_dump_json()
        result = kernel.validate_boundary(
            stale, UnitManifest, workflow="prepare", compatibility=metadata
        )
        self.assertEqual(result.error.code, "incompatible-artifact-version")
        incompatible_name = kernel.validate_boundary(
            valid_manifest().model_dump_json(),
            UnitManifest,
            workflow="prepare",
            compatibility=CompatibilityMetadata(contract_name="context-bundle", accepted_versions=(1,)),
        )
        self.assertEqual(incompatible_name.error.code, "incompatible-artifact-contract")
        self.assertEqual(incompatible_name.error.rule, "contract-name-match")
        for versions in ((0,), (1, 1)):
            with self.subTest(versions=versions), self.assertRaises(ValidationError):
                CompatibilityMetadata(contract_name="unit-manifest", accepted_versions=versions)

        known = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        self.assertEqual(kernel.source_text_digest("hello"), known)
        self.assertIsNone(kernel.guard_source_text("hello", known, workflow="prepare").error)
        mismatch = kernel.guard_source_text("hello\n", known, workflow="prepare")
        self.assertEqual(mismatch.error.code, "source-text-digest-mismatch")
        self.assertNotEqual(mismatch.error.observed, known)
        malformed_digest = kernel.guard_source_text("hello", "not-a-digest", workflow="prepare")
        self.assertEqual(malformed_digest.error.code, "malformed-source-text-digest")
        surrogate = kernel.guard_source_text("\ud800", known, workflow="prepare")
        self.assertEqual(surrogate.error.rule, "source-text-utf8")

    def test_feature_kernel_error_is_preserved(self) -> None:
        preserved = actionable_error(
            code="feature-domain-error",
            workflow="prepare",
            subject="unit",
            rule="fixture-rule",
            expected="expected",
            observed="observed",
            next_action="fix fixture",
        )

        def feature(_: UnitManifest) -> None:
            raise kernel.KernelValidationError(preserved)

        result = kernel.run_boundary(
            valid_manifest().model_dump_json(), UnitManifest, feature, workflow="prepare"
        )
        self.assertEqual(result.error, preserved)


class LifecycleTests(unittest.TestCase):
    def test_complete_transition_table(self) -> None:
        normal = {
            kernel.UnitLifecycleState.PREPARED: {kernel.UnitLifecycleState.PROPOSED},
            kernel.UnitLifecycleState.PROPOSED: {kernel.UnitLifecycleState.EVALUATED},
            kernel.UnitLifecycleState.EVALUATED: {
                kernel.UnitLifecycleState.COMMITTED,
                kernel.UnitLifecycleState.RECOVERY_PENDING,
            },
            kernel.UnitLifecycleState.RECOVERY_PENDING: {kernel.UnitLifecycleState.RECOVERY_PROPOSED},
            kernel.UnitLifecycleState.RECOVERY_PROPOSED: {kernel.UnitLifecycleState.RECOVERY_EVALUATED},
            kernel.UnitLifecycleState.RECOVERY_EVALUATED: {kernel.UnitLifecycleState.COMMITTED},
            kernel.UnitLifecycleState.COMMITTED: set(),
            kernel.UnitLifecycleState.FAILED: set(),
        }
        for current in kernel.UnitLifecycleState:
            expected_next = frozenset(normal[current])
            if current not in kernel.TERMINAL_STATES:
                expected_next |= frozenset({kernel.UnitLifecycleState.FAILED})
            self.assertEqual(kernel.legal_next_states(current), expected_next)
            for target in kernel.UnitLifecycleState:
                is_normal = target in normal[current]
                if is_normal:
                    self.assertEqual(kernel.validate_transition(current, target), target)
                elif target is kernel.UnitLifecycleState.FAILED and current not in kernel.TERMINAL_STATES:
                    self.assertEqual(
                        kernel.validate_transition(current, target, failure_code="retry-exhausted"), target
                    )
                    with self.assertRaises(kernel.KernelValidationError):
                        kernel.validate_transition(current, target)
                else:
                    with self.assertRaises(kernel.KernelValidationError):
                        kernel.validate_transition(current, target)

    def test_malformed_lifecycle_states_have_stable_errors(self) -> None:
        for call in (
            lambda: kernel.legal_next_states("prepared"),
            lambda: kernel.validate_transition("prepared", kernel.UnitLifecycleState.PROPOSED),
            lambda: kernel.validate_transition(kernel.UnitLifecycleState.PREPARED, "proposed"),
        ):
            with self.assertRaises(kernel.KernelValidationError) as captured:
                call()
            self.assertEqual(captured.exception.error.code, "illegal-transition")
            self.assertEqual(captured.exception.error.rule, "lifecycle-state-type")
