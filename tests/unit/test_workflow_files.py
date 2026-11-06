import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

WORKFLOWS = sorted([*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")])

needs_git_source = pytest.mark.skipif(
    "source = { git ="
    not in (REPO_ROOT / "uv.lock").read_text(encoding="utf-8"),
    reason="uv.lock holds no git source: nwp-core comes from an index, so the"
    " read-token workflow rules no longer apply",
)

# GitHub resolves secret names case-insensitively, in dot and bracket form.
_TOKEN_REFERENCE = re.compile(
    r"secrets\s*(?:\.\s*NWP_CORE_READ_TOKEN\b"
    r"|\[\s*['\"]NWP_CORE_READ_TOKEN['\"]\s*\])",
    re.IGNORECASE,
)
_SHA_PINNED = re.compile(r"[^@\s]+@[0-9a-f]{40}")
_DIGEST_PINNED_IMAGE = re.compile(r"docker://[^@\s]+@sha256:[0-9a-f]{64}")

_Location = tuple[str | int, ...]


def _jobs(doc: dict[str, object]) -> dict[str, dict[str, Any]]:
    return cast("dict[str, dict[str, Any]]", doc["jobs"])


def _steps(doc: dict[str, object]) -> Iterator[tuple[str, int, dict[str, Any]]]:
    for job_id, job in _jobs(doc).items():
        for index, step in enumerate(job.get("steps", [])):
            yield job_id, index, step


def _uses(doc: dict[str, object]) -> Iterator[tuple[str, str]]:
    for job_id, job in _jobs(doc).items():
        if "uses" in job:
            yield f"jobs.{job_id}", job["uses"]
        for index, step in enumerate(job.get("steps", [])):
            if "uses" in step:
                yield f"jobs.{job_id}.steps[{index}]", step["uses"]


def _strings(
    node: object, location: _Location = ()
) -> Iterator[tuple[_Location, str]]:
    if isinstance(node, str):
        yield location, node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from _strings(value, (*location, key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _strings(value, (*location, index))


def check_triggers(doc: dict[str, object]) -> list[str]:
    # PyYAML follows YAML 1.1 and reads the bare key `on` as True: looking
    # up "on" alone finds nothing and passes vacuously.
    triggers: Any = doc.get("on", cast("dict[object, object]", doc).get(True))
    names = [triggers] if isinstance(triggers, str) else triggers
    return [
        f"triggers: `{name}` is an untrusted trigger"
        for name in ("pull_request_target", "workflow_run")
        if name in names
    ]


def check_setup_uv_cache(doc: dict[str, object]) -> list[str]:
    violations = []
    for job_id, index, step in _steps(doc):
        if not step.get("uses", "").startswith("astral-sh/setup-uv@"):
            continue
        cache = step.get("with", {}).get("enable-cache")
        if cache is not False and cache != "false":
            violations.append(
                f"setup-uv-cache: jobs.{job_id}.steps[{index}] sets"
                f" enable-cache to {cache!r}, expected false"
            )
    return violations


def check_caches(doc: dict[str, object]) -> list[str]:
    violations = [
        f"caches: jobs.{job_id}.steps[{index}] uses {step['uses']}"
        for job_id, index, step in _steps(doc)
        if step.get("uses", "").startswith(
            ("actions/cache", "actions/upload-artifact")
        )
    ]
    violations += [
        f"caches: type=gha cache at {'.'.join(map(str, location))}"
        for location, text in _strings(doc["jobs"], ("jobs",))
        if "type=gha" in text
    ]
    return violations


def check_permissions(doc: dict[str, object]) -> list[str]:
    permissions = doc.get("permissions")
    if permissions == {"contents": "read"}:
        return []
    return [
        f"permissions: top-level permissions is {permissions!r},"
        " expected exactly {'contents': 'read'}"
    ]


def check_token_scope(doc: dict[str, object]) -> list[str]:
    violations = []
    for location, text in _strings(doc):
        in_step_env = (
            len(location) == 6
            and location[0] == "jobs"
            and location[2] == "steps"
            and location[4] == "env"
        )
        if _TOKEN_REFERENCE.search(text) and not in_step_env:
            violations.append(
                "token-scope: secrets.NWP_CORE_READ_TOKEN at"
                f" {'.'.join(map(str, location))}, allowed only at"
                " jobs.<job>.steps[<i>].env.<name>"
            )
    return violations


def check_secrets_inherit(doc: dict[str, object]) -> list[str]:
    return [
        f"secrets-inherit: jobs.{job_id} passes every secret to {job['uses']}"
        for job_id, job in _jobs(doc).items()
        if job.get("secrets") == "inherit"
    ]


def check_action_pins(doc: dict[str, object]) -> list[str]:
    return [
        f"action-pins: {where} uses {ref}, expected a full commit SHA"
        for where, ref in _uses(doc)
        if not (
            ref.startswith("./")
            or _SHA_PINNED.fullmatch(ref)
            or _DIGEST_PINNED_IMAGE.fullmatch(ref)
        )
    ]


def check_checkout_credentials(doc: dict[str, object]) -> list[str]:
    violations = []
    for job_id, index, step in _steps(doc):
        if not step.get("uses", "").startswith("actions/checkout@"):
            continue
        persist = step.get("with", {}).get("persist-credentials")
        if persist is not False and persist != "false":
            violations.append(
                f"checkout-credentials: jobs.{job_id}.steps[{index}] sets"
                f" persist-credentials to {persist!r}, expected false"
            )
    return violations


def check_job_permissions(doc: dict[str, object]) -> list[str]:
    return [
        f"job-permissions: jobs.{job_id} overrides the top-level permissions"
        for job_id, job in _jobs(doc).items()
        if "permissions" in job
    ]


def check_run_expressions(doc: dict[str, object]) -> list[str]:
    # An expression in `run:` is pasted into the script before the shell
    # parses it; pass the value through the step's `env:` instead.
    return [
        f"run-expressions: jobs.{job_id}.steps[{index}].run holds an expression"
        for job_id, index, step in _steps(doc)
        if "${{" in step.get("run", "")
    ]


def test_workflows_directory_is_not_empty() -> None:
    assert WORKFLOWS, f"no workflow file under {WORKFLOW_DIR}"


@needs_git_source
@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_triggers_are_trusted(workflow: Path) -> None:
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))

    assert check_triggers(doc) == []


@needs_git_source
@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_setup_uv_disables_cache(workflow: Path) -> None:
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))

    assert check_setup_uv_cache(doc) == []


@needs_git_source
@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_has_no_cache_or_artifact(workflow: Path) -> None:
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))

    assert check_caches(doc) == []


@needs_git_source
@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_permissions_are_read_only(workflow: Path) -> None:
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))

    assert check_permissions(doc) == []


@needs_git_source
@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_token_scope_is_step_env(workflow: Path) -> None:
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))

    assert check_token_scope(doc) == []


@pytest.mark.parametrize(
    "check",
    [
        check_secrets_inherit,
        check_action_pins,
        check_checkout_credentials,
        check_job_permissions,
        check_run_expressions,
    ],
)
@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_passes_hygiene_check(
    workflow: Path, check: Callable[[dict[str, object]], list[str]]
) -> None:
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))

    assert check(doc) == []


@pytest.mark.parametrize(
    "triggers",
    [
        "on: pull_request_target",
        "on: [push, workflow_run]",
        "on:\n  workflow_run:\n    workflows: [ci]",
    ],
    ids=["string", "list", "mapping"],
)
def test_check_triggers_flags_untrusted_trigger(triggers: str) -> None:
    violations = check_triggers(yaml.safe_load(triggers))

    assert len(violations) == 1


def test_check_setup_uv_cache_flags_enabled_cache() -> None:
    doc = yaml.safe_load(
        """
        jobs:
          lint:
            steps:
              - uses: astral-sh/setup-uv@v1
                with:
                  enable-cache: true
        """
    )

    violations = check_setup_uv_cache(doc)

    assert len(violations) == 1
    assert "jobs.lint.steps[0]" in violations[0]


def test_check_caches_flags_cache_action() -> None:
    doc = yaml.safe_load(
        """
        jobs:
          test:
            steps:
              - run: echo ready
              - uses: actions/cache@v4
        """
    )

    violations = check_caches(doc)

    assert len(violations) == 1
    assert "jobs.test.steps[1]" in violations[0]


def test_check_caches_flags_gha_cache_string() -> None:
    doc = yaml.safe_load(
        """
        jobs:
          image:
            steps:
              - run: docker buildx build --cache-to type=gha .
        """
    )

    violations = check_caches(doc)

    assert len(violations) == 1
    assert "jobs.image.steps.0.run" in violations[0]


def test_check_permissions_flags_wider_permissions() -> None:
    doc = yaml.safe_load(
        """
        permissions:
          contents: write
        jobs: {}
        """
    )

    assert len(check_permissions(doc)) == 1


def test_check_token_scope_flags_job_level_env() -> None:
    doc = yaml.safe_load(
        """
        jobs:
          build:
            env:
              LEAK: ${{ secrets.NWP_CORE_READ_TOKEN }}
            steps:
              - run: echo ready
        """
    )

    violations = check_token_scope(doc)

    assert len(violations) == 1
    assert "jobs.build.env.LEAK" in violations[0]


@pytest.mark.parametrize(
    "reference",
    [
        "${{ secrets['NWP_CORE_READ_TOKEN'] }}",
        '${{ secrets[ "NWP_CORE_READ_TOKEN" ] }}',
        "${{ secrets.nwp_core_read_token }}",
    ],
    ids=["bracket", "bracket-double-quote", "lower-case"],
)
def test_check_token_scope_flags_other_reference_forms(reference: str) -> None:
    doc: dict[str, object] = {
        "jobs": {"build": {"env": {"LEAK": reference}, "steps": []}}
    }

    assert len(check_token_scope(doc)) == 1


def test_check_token_scope_allows_step_env() -> None:
    doc = yaml.safe_load(
        """
        jobs:
          build:
            steps:
              - env:
                  TOKEN: ${{ secrets.NWP_CORE_READ_TOKEN }}
                run: echo ready
        """
    )

    assert check_token_scope(doc) == []


def test_check_secrets_inherit_flags_inherit() -> None:
    doc = yaml.safe_load(
        """
        jobs:
          call:
            uses: ./.github/workflows/reusable.yml
            secrets: inherit
        """
    )

    violations = check_secrets_inherit(doc)

    assert len(violations) == 1
    assert "jobs.call" in violations[0]


@pytest.mark.parametrize(
    "ref",
    [
        "actions/checkout@v4",
        "actions/checkout@main",
        "actions/checkout@3d3c42e",
        "docker://alpine:3.20",
        "owner/repo/.github/workflows/ci.yml@v1",
    ],
    ids=["tag", "branch", "short-sha", "image-tag", "reusable-tag"],
)
def test_check_action_pins_flags_unpinned_ref(ref: str) -> None:
    doc: dict[str, object] = {"jobs": {"build": {"steps": [{"uses": ref}]}}}

    assert len(check_action_pins(doc)) == 1


@pytest.mark.parametrize(
    "ref",
    [
        "actions/checkout@" + "a" * 40,
        "owner/repo/.github/workflows/ci.yml@" + "b" * 40,
        "docker://alpine@sha256:" + "c" * 64,
        "./.github/actions/local",
    ],
    ids=["sha", "reusable-sha", "image-digest", "local"],
)
def test_check_action_pins_allows_pinned_ref(ref: str) -> None:
    doc: dict[str, object] = {"jobs": {"build": {"steps": [{"uses": ref}]}}}

    assert check_action_pins(doc) == []


def test_check_action_pins_flags_job_level_reusable_workflow() -> None:
    doc: dict[str, object] = {
        "jobs": {"call": {"uses": "owner/repo/.github/workflows/ci.yml@main"}}
    }

    violations = check_action_pins(doc)

    assert len(violations) == 1
    assert violations[0].startswith("action-pins: jobs.call uses")


@pytest.mark.parametrize(
    "with_block",
    ["{}", "{persist-credentials: true}"],
    ids=["default", "true"],
)
def test_check_checkout_credentials_flags_persisted_credentials(
    with_block: str,
) -> None:
    doc = yaml.safe_load(
        f"""
        jobs:
          test:
            steps:
              - uses: actions/checkout@{"a" * 40}
                with: {with_block}
        """
    )

    violations = check_checkout_credentials(doc)

    assert len(violations) == 1
    assert "jobs.test.steps[0]" in violations[0]


def test_check_job_permissions_flags_job_override() -> None:
    doc = yaml.safe_load(
        """
        jobs:
          release:
            permissions:
              contents: write
            steps: []
        """
    )

    violations = check_job_permissions(doc)

    assert len(violations) == 1
    assert "jobs.release" in violations[0]


def test_check_run_expressions_flags_interpolated_run() -> None:
    doc = yaml.safe_load(
        """
        jobs:
          greet:
            steps:
              - env:
                  TITLE: ${{ github.event.pull_request.title }}
                run: echo "$TITLE"
              - run: echo "${{ github.event.pull_request.title }}"
        """
    )

    violations = check_run_expressions(doc)

    assert len(violations) == 1
    assert "jobs.greet.steps[1].run" in violations[0]
