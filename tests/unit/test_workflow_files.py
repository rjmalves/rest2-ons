from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

if "source = { git =" not in (REPO_ROOT / "uv.lock").read_text(
    encoding="utf-8"
):
    pytest.skip(
        "uv.lock holds no git source: nwp-core comes from an index, so the"
        " read-token workflow rules no longer apply",
        allow_module_level=True,
    )

WORKFLOWS = sorted([*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")])

_Location = tuple[str | int, ...]


def _steps(doc: dict[str, object]) -> Iterator[tuple[str, int, dict[str, Any]]]:
    jobs = cast("dict[str, dict[str, Any]]", doc["jobs"])
    for job_id, job in jobs.items():
        for index, step in enumerate(job.get("steps", [])):
            yield job_id, index, step


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
        if "secrets.NWP_CORE_READ_TOKEN" in text and not in_step_env:
            violations.append(
                "token-scope: secrets.NWP_CORE_READ_TOKEN at"
                f" {'.'.join(map(str, location))}, allowed only at"
                " jobs.<job>.steps[<i>].env.<name>"
            )
    return violations


def test_workflows_directory_is_not_empty() -> None:
    assert WORKFLOWS, f"no workflow file under {WORKFLOW_DIR}"


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_triggers_are_trusted(workflow: Path) -> None:
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))

    assert check_triggers(doc) == []


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_setup_uv_disables_cache(workflow: Path) -> None:
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))

    assert check_setup_uv_cache(doc) == []


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_has_no_cache_or_artifact(workflow: Path) -> None:
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))

    assert check_caches(doc) == []


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_permissions_are_read_only(workflow: Path) -> None:
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))

    assert check_permissions(doc) == []


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_token_scope_is_step_env(workflow: Path) -> None:
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))

    assert check_token_scope(doc) == []


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
