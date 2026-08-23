# Technology Currentness Review

**Target:** `ARCHITECTURE-SPINE.md`  
**Lens:** committed technology/version and current-library assertions  
**Reviewed:** 2026-08-23  
**Verdict:** **CHANGES REQUESTED** — the selected stack is real, current, and compatible with this Windows/CPython 3.14 environment, but its exact-version and strict-validation commitments are not yet represented by an executable package manifest or lock file.

## Reality-check result

| Committed technology | Result | Evidence |
| --- | --- | --- |
| Python 3.14.4 | Exists; locally installed (`python --version` reports `Python 3.14.4`). | [Python 3.14.4 release](https://www.python.org/downloads/release/python-3144/) |
| uv 0.11.19 | Exists; locally installed (`uv --version` reports `uv 0.11.19`). | [uv 0.11.19 release](https://github.com/astral-sh/uv/releases/tag/0.11.19) |
| Pydantic 2.13.4 | Exists; supports Python >=3.9 and lists Python 3.14 support. | [Pydantic 2.13.4 on PyPI](https://pypi.org/project/pydantic/2.13.4/) |
| lxml 6.1.2 | Exists; released 2026-08-19, requires Python >=3.8, and publishes a `cp314-cp314-win_amd64` wheel. | [lxml 6.1.2 on PyPI](https://pypi.org/project/lxml/6.1.2/) |

The repository does not yet contain `src/i18n-pipeline/`, `pyproject.toml`, or `uv.lock`; neither Pydantic nor lxml is installed in the base interpreter. That is expected for an architecture seed, but it means the commitments have not been made reproducible yet.

## Findings

### [P1] Exact stack pins are not enforceable until the seeded package and lock file exist

**Locations:** AD-7, lines 75–79; Stack, lines 182–189; Structural Seed, lines 193–196.

The document commits to four exact releases, while its proposed `src/i18n-pipeline/pyproject.toml` and `uv.lock` are only a future directory sketch. The local repository confirms that the package directory and lock file are absent. Consequently, an implementation can currently resolve different Pydantic/lxml versions, or a different Python constraint, while still appearing to follow the spine. Create the seed before implementation and commit a generated `uv.lock`; declare the interpreter constraint and exact direct dependencies in `pyproject.toml`. This turns the researched current choices into reproducible build inputs.

### [P1] “Strict frozen Pydantic boundary models” is underspecified and can silently allow coercion or unknown fields

**Location:** AD-7, line 79.

Pydantic’s immutability and strictness are separate controls: `frozen` prevents reassignment after construction, while strict mode must be configured independently; rejecting extra fields is another independent setting. The spine needs a normative boundary-model configuration (at minimum model-level `strict=True`, `frozen=True`, and `extra='forbid'`), plus contract tests proving that coercible inputs and unknown fields are rejected. Without it, the phrase “strict frozen” is easy to implement as only `frozen=True`, contrary to the canonical-object/unknown-field rules. Current documentation confirms the separate frozen and strict controls: [Pydantic fields](https://docs.pydantic.dev/latest/concepts/fields/) and [strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/).

### [P2] The lxml identity recorded in a Run Snapshot needs its native-library build identity, not only `lxml==6.1.2`

**Location:** AD-13, line 115.

The architecture correctly says parser/serializer identity is frozen, but the specified identity is only the Python-package version. lxml is a binding to libxml2/libxslt, so version/package identity alone does not establish the native parser/serializer behavior for a run, especially if a source build is used or the runtime platform changes. Define the snapshot fields and a startup assertion: lxml version, `LIBXML_VERSION`, `LIBXSLT_VERSION` where applicable, Python implementation/version, platform/ABI, and a deterministic serialization fixture digest. The verified Windows wheel makes the selected release feasible, but does not itself make a cross-platform run reproducible. [lxml project metadata](https://pypi.org/project/lxml/6.1.2/)

## Conclusion

No stale or nonexistent version was found: Python 3.14.4, Pydantic 2.13.4, lxml 6.1.2, and uv 0.11.19 all exist and fit together on the current local host. Address the two P1 issues before treating the stack as an enforceable architecture commitment.

## Post-fix verification

**Result: PASS.**

- **P1 — enforceable pins:** Safely gated. AD-7 now makes creation of `pyproject.toml`, committed `uv.lock`, component-identity lock digest, and dependency/serialization startup checks mandatory before feature work or live mode.
- **P1 — Pydantic boundary behavior:** Resolved. AD-7 now normatively requires `ConfigDict(strict=True, frozen=True, extra='forbid')` and proof that coercible and unknown inputs fail.
- **P2 — lxml/native runtime identity:** Resolved. The Component Identity contract now requires Python/platform/ABI, lock digest, lxml, `LIBXML_VERSION`, `LIBXSLT_VERSION`, and an HTML serialization fixture digest; AD-22 rejects live-mode drift.

No high or critical technology-currentness finding remains. The package and lock file still need to be created during implementation, but the spine now blocks feature/live progress until that prerequisite is satisfied.
