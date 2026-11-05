import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

from tests.conftest import load_ci_script

pytestmark = pytest.mark.unit

TAG = "v0.5.0"
MARKER = "# --- tool-specific entries: edit in each copy ---"
SHA_A = "a" * 40
SHA_B = "b" * 40
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64


@pytest.fixture
def check(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_ci_script("check_template_copies", monkeypatch)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=tester",
            "-c",
            "user.email=tester@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "tag.gpgsign=false",
            "-C",
            str(repo),
            *args,
        ],
        check=True,
        capture_output=True,
    )


def _build_checkout(
    check: ModuleType, root: Path, *, grow: str | None = None
) -> Path:
    root.mkdir()
    _git(root, "init", "-q")
    for pair in check.PAIRS:
        template = root / "templates" / pair.template_id
        template.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(check.REPO_ROOT / pair.copy, template)
    if grow is not None:
        with (root / "templates" / grow).open("a", encoding="utf-8") as handle:
            handle.write("# a line the copy lacks\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "templates")
    _git(root, "tag", TAG)
    return root


@pytest.fixture
def checkout(check: ModuleType, tmp_path: Path) -> Path:
    return _build_checkout(check, tmp_path / "nwp-core")


def _rule(check: ModuleType, template_id: str) -> object:
    return {pair.template_id: pair.rule for pair in check.PAIRS}[template_id]


def test_differences_identical_copy_conforms(check: ModuleType) -> None:
    text = "alpha\nbeta\ngamma\n"

    assert check.differences(text, text, None) == []


def test_differences_changed_line_is_reported_with_its_number(
    check: ModuleType,
) -> None:
    assert check.differences("a\nb\nc\n", "a\nX\nc\n", None) == [2]


@pytest.mark.parametrize(
    ("template_id", "template_line", "copy_line"),
    [
        (
            "ci.yml",
            "      IMPORT_CHAIN: import __PACKAGE__\n",
            "      IMPORT_CHAIN: import tool._cli, numpy\n",
        ),
        (
            "Dockerfile",
            'ENTRYPOINT ["__CONSOLE_SCRIPT__"]\n',
            'ENTRYPOINT ["tool"]\n',
        ),
    ],
)
def test_differences_prefix_edit_point_may_differ(
    check: ModuleType, template_id: str, template_line: str, copy_line: str
) -> None:
    rule = _rule(check, template_id)

    template = f"first\n{template_line}last\n"
    assert check.differences(template, f"first\n{copy_line}last\n", rule) == []
    assert check.differences(template, f"FIRST\n{copy_line}last\n", rule) == [1]


def test_differences_prefix_edit_point_must_sit_at_the_same_line(
    check: ModuleType,
) -> None:
    rule = _rule(check, "Dockerfile")
    template = 'first\nENTRYPOINT ["__CONSOLE_SCRIPT__"]\nlast\n'
    copy = 'ENTRYPOINT ["tool"]\nfirst\nlast\n'

    assert check.differences(template, copy, rule) == [1, 2]


def test_differences_tail_section_may_differ(check: ModuleType) -> None:
    rule = _rule(check, "allowed-deps.txt")
    template = f"head\n{MARKER}\n"

    assert check.differences(template, f"head\n{MARKER}\nx\ny\n", rule) == []


def test_differences_change_above_the_tail_marker_is_reported(
    check: ModuleType,
) -> None:
    rule = _rule(check, "allowed-deps.txt")
    template = f"head\n{MARKER}\n"

    assert check.differences(template, f"HEAD\n{MARKER}\nx\n", rule) == [1]


@pytest.mark.parametrize(
    ("template", "copy"),
    [
        ("head\n", f"head\n{MARKER}\nx\n"),
        (f"head\n{MARKER}\n", "head\nx\n"),
    ],
    ids=["template-without-marker", "copy-without-marker"],
)
def test_differences_tail_marker_missing_is_reported_at_line_one(
    check: ModuleType, template: str, copy: str
) -> None:
    assert check.differences(
        template, copy, _rule(check, "allowed-deps.txt")
    ) == [1]


def test_differences_refreshed_action_sha_with_version_comment_conforms(
    check: ModuleType,
) -> None:
    template = f"      - uses: actions/checkout@{SHA_A} # v7.0.1\n"
    copy = f"      - uses: actions/checkout@{SHA_B} # v8.1.0\n"

    assert check.differences(template, copy, None) == []


def test_differences_refreshed_image_digest_conforms(check: ModuleType) -> None:
    template = f"FROM python:3.12-slim@sha256:{DIGEST_C} AS builder\n"
    copy = f"FROM python:3.12-slim@sha256:{DIGEST_D} AS builder\n"

    assert check.differences(template, copy, None) == []


@pytest.mark.parametrize(
    ("template", "copy"),
    [
        (
            f"      - uses: actions/checkout@{SHA_A} # v7.0.1\n",
            f"      - uses: actions/cache@{SHA_B} # v7.0.1\n",
        ),
        (
            f"      - uses: actions/checkout@{SHA_A} # v7.0.1\n",
            f"      - uses: actions/checkout@{SHA_B} # v7.0.1 pinned\n",
        ),
        (
            f"FROM python:3.12-slim@sha256:{DIGEST_C}\n",
            f"FROM python:3.13-slim@sha256:{DIGEST_D}\n",
        ),
    ],
    ids=["other-action", "extra-comment-text", "other-image-tag"],
)
def test_differences_pin_line_with_another_change_is_reported(
    check: ModuleType, template: str, copy: str
) -> None:
    assert check.differences(template, copy, None) == [1]


def test_differences_appended_line_is_reported(check: ModuleType) -> None:
    assert check.differences("a\nb\n", "a\nb\nc\n", None) == [3]


def test_differences_missing_line_is_reported(check: ModuleType) -> None:
    assert check.differences("a\nb\nc\n", "a\nb\n", None) == [3]


def test_main_exits_0_when_every_copy_conforms(
    check: ModuleType, checkout: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert check.main([str(checkout)]) == 0
    assert capsys.readouterr().out == (
        "check_template_copies: 8 copies conform to v0.5.0\n"
    )


def test_main_exits_1_and_names_the_copy_when_the_template_gains_a_line(
    check: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    grown = _build_checkout(check, tmp_path / "grown", grow="check_image.py")
    copy_lines = (
        (check.REPO_ROOT / "ci" / "check_image.py")
        .read_text(encoding="utf-8")
        .splitlines()
    )

    assert check.main([str(grown)]) == 1
    assert capsys.readouterr().out.splitlines() == [
        f"ci/check_image.py:{len(copy_lines) + 1}: differs from "
        "templates/check_image.py at v0.5.0",
        "check_template_copies: 1 of 8 copies differ from v0.5.0",
    ]


def test_main_reports_a_missing_copy(
    check: ModuleType,
    checkout: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    monkeypatch.setattr(check, "REPO_ROOT", empty_root)

    assert check.main([str(checkout)]) == 1
    out = capsys.readouterr().out.splitlines()
    assert "Dockerfile: missing" in out
    assert out[-1] == "check_template_copies: 8 of 8 copies differ from v0.5.0"


@pytest.mark.parametrize("case", ["missing-tag", "not-a-repository", "no-dir"])
def test_main_exits_2_when_the_templates_cannot_be_read(
    check: ModuleType,
    checkout: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    case: str,
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    argv = {
        "missing-tag": [str(checkout), "--tag", "v9.9.9"],
        "not-a-repository": [str(plain)],
        "no-dir": [str(tmp_path / "absent")],
    }[case]

    assert check.main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("check_template_copies: ")
