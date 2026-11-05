import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.conftest import load_ci_script

pytestmark = pytest.mark.unit

INIT = "src/rest2_ons/__init__.py"
VERSION = "src/rest2_ons/_version.py"
TAGS = ["v0.2.0", "v0.1.0"]
CHANGELOG = """\
# Changelog

## [Unreleased]

### Breaking

- `rest2_ons.f` removed in the next minor.
- Dropped `rest2_ons.nope` mid-sentence.
- `other.pkg` is not a rest2_ons name.

### Added

- `rest2_ons.h` new helper.

## [0.2.0] - 2026-11-01

### Breaking

- `rest2_ons.g` renamed while releasing.

## [0.1.0] - 2026-10-30

### Breaking

- `rest2_ons.old` removed long ago.
"""


def _breaking(*names: str) -> str:
    bullets = "".join(f"- `rest2_ons.{name}` removed.\n" for name in names)
    return f"## [Unreleased]\n\n### Breaking\n\n{bullets}"


@pytest.fixture
def check(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_ci_script("check_api_diff", monkeypatch)


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


def _write(
    repo: Path,
    names: tuple[str, ...] | str,
    version: str,
    changelog: str,
) -> None:
    source = names if isinstance(names, str) else f"__all__ = {list(names)!r}\n"
    (repo / INIT).parent.mkdir(parents=True, exist_ok=True)
    (repo / INIT).write_text(source, encoding="utf-8")
    (repo / VERSION).write_text(
        f'__version__ = "{version}"\n', encoding="utf-8"
    )
    (repo / "CHANGELOG.md").write_text(changelog, encoding="utf-8")


def _commit(
    repo: Path,
    names: tuple[str, ...] | str,
    *,
    version: str = "0.1.0",
    changelog: str = "",
    tag: str | None = None,
) -> None:
    _write(repo, names, version, changelog)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "state")
    if tag is not None:
        _git(repo, "tag", tag)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    _git(path, "init", "-q")
    return path


def _run(
    check: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str, str]:
    code = check.main(["--repo", str(repo)])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_parse_all_reads_a_list_literal(check: ModuleType) -> None:
    assert check.parse_all('__all__ = ["b", "a"]\n') == frozenset({"a", "b"})


def test_parse_all_reads_a_tuple_literal(check: ModuleType) -> None:
    assert check.parse_all('import os\n__all__ = ("a",)\n') == frozenset({"a"})


@pytest.mark.parametrize(
    "source",
    ["x = 1\n", "__all__ = [*OTHER]\n", "__all__ = [1]\n", "__all__ = {'a'}\n"],
    ids=["missing", "starred", "non-string", "set"],
)
def test_parse_all_rejects_anything_but_a_literal_list_of_strings(
    check: ModuleType, source: str
) -> None:
    with pytest.raises(check.CheckError):
        check.parse_all(source)


def test_parse_version_reads_the_literal(check: ModuleType) -> None:
    assert check.parse_version('__version__ = "0.1.0"\n') == "0.1.0"


@pytest.mark.parametrize(
    "source",
    ["x = 1\n", "__version__ = get()\n", "__version__ = 1\n"],
    ids=["missing", "call", "non-string"],
)
def test_parse_version_rejects_anything_but_a_string_literal(
    check: ModuleType, source: str
) -> None:
    with pytest.raises(check.CheckError):
        check.parse_version(source)


@pytest.mark.parametrize(
    ("tags", "at_head", "expected"),
    [
        (TAGS, {"v0.2.0"}, "v0.1.0"),
        (TAGS, set(), "v0.2.0"),
        (TAGS, {"v0.2.0", "v0.1.0"}, None),
        ([], set(), None),
    ],
)
def test_pick_base_skips_the_tags_at_head(
    check: ModuleType,
    tags: list[str],
    at_head: set[str],
    expected: str | None,
) -> None:
    assert check.pick_base(tags, at_head) == expected


@pytest.mark.parametrize(
    ("tags", "at_head", "expected"),
    [
        (["v0.1.0"], set(), True),
        (TAGS, {"v0.2.0"}, True),
        (TAGS, set(), False),
    ],
)
def test_is_releasing_when_the_version_tag_is_absent_or_at_head(
    check: ModuleType, tags: list[str], at_head: set[str], expected: bool
) -> None:
    assert check.is_releasing("0.2.0", tags, at_head) is expected


def test_allowed_breaks_reads_only_unreleased_while_not_releasing(
    check: ModuleType,
) -> None:
    assert check.allowed_breaks(CHANGELOG, "0.2.0", False) == {"rest2_ons.f"}


def test_allowed_breaks_adds_the_released_section_while_releasing(
    check: ModuleType,
) -> None:
    assert check.allowed_breaks(CHANGELOG, "0.2.0", True) == {
        "rest2_ons.f",
        "rest2_ons.g",
    }


def test_allowed_breaks_never_reads_an_older_release_section(
    check: ModuleType,
) -> None:
    assert "rest2_ons.old" not in check.allowed_breaks(CHANGELOG, "0.2.0", True)


def test_allowed_breaks_ignores_bullets_outside_the_breaking_subsection(
    check: ModuleType,
) -> None:
    assert "rest2_ons.h" not in check.allowed_breaks(CHANGELOG, "0.2.0", True)


def test_unallowed_reports_a_removal_without_a_bullet(
    check: ModuleType,
) -> None:
    removed = ["rest2_ons.f", "rest2_ons.ff"]

    assert check.unallowed(removed, {"rest2_ons.ff"}, "0.2.0", "v0.1.0") == [
        "rest2_ons.f"
    ]


def test_unallowed_is_empty_when_every_removal_has_a_bullet(
    check: ModuleType,
) -> None:
    assert (
        check.unallowed(["rest2_ons.f"], {"rest2_ons.f"}, "0.2.0", "v0.1.0")
        == []
    )


def test_unallowed_ignores_bullets_inside_the_base_major(
    check: ModuleType,
) -> None:
    assert check.unallowed(
        ["rest2_ons.f"], {"rest2_ons.f"}, "1.1.0", "v1.0.0"
    ) == ["rest2_ons.f"]


def test_unallowed_honours_bullets_across_a_major_bump(
    check: ModuleType,
) -> None:
    assert (
        check.unallowed(["rest2_ons.f"], {"rest2_ons.f"}, "2.0.0", "v1.4.0")
        == []
    )


def test_unallowed_rejects_a_version_without_a_major(
    check: ModuleType,
) -> None:
    with pytest.raises(check.CheckError, match="major"):
        check.unallowed(["rest2_ons.f"], set(), "next", "v0.1.0")


def test_main_without_a_tag_prints_nothing_and_exits_0(
    check: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(repo, ("alpha",))

    assert _run(check, repo, capsys) == (0, "", "")


def test_main_with_only_a_tag_at_head_prints_nothing_and_exits_0(
    check: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(repo, ("alpha",), tag="v0.1.0")

    assert _run(check, repo, capsys) == (0, "", "")


def test_main_fails_on_a_removal_without_a_bullet_and_names_it(
    check: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(repo, ("alpha", "beta"), tag="v0.1.0")
    _commit(repo, ("alpha",), version="0.2.0", changelog=_breaking("alpha"))

    assert _run(check, repo, capsys) == (
        1,
        "- rest2_ons.beta\n"
        "check_api_diff: rest2_ons.beta removed since v0.1.0 "
        "without a ### Breaking entry\n",
        "",
    )


def test_main_passes_a_removal_with_an_unreleased_bullet(
    check: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(repo, ("alpha", "beta"), tag="v0.1.0")
    _commit(repo, ("alpha",), version="0.2.0", changelog=_breaking("beta"))

    assert _run(check, repo, capsys) == (0, "- rest2_ons.beta\n", "")


def test_main_passes_a_removal_listed_in_the_section_being_released(
    check: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(repo, ("alpha", "beta"), tag="v0.1.0")
    released = (
        "## [0.2.0] - 2026-11-01\n\n### Breaking\n\n- `rest2_ons.beta`.\n"
    )
    _commit(repo, ("alpha",), version="0.2.0", changelog=released, tag="v0.2.0")

    assert _run(check, repo, capsys) == (0, "- rest2_ons.beta\n", "")


def test_main_passes_an_addition_and_prints_it(
    check: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(repo, ("alpha",), tag="v0.1.0")
    _commit(repo, ("alpha", "gamma"), version="0.2.0")

    assert _run(check, repo, capsys) == (0, "+ rest2_ons.gamma\n", "")


def test_main_prints_removals_before_additions_each_sorted(
    check: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(repo, ("alpha", "delta", "beta"), tag="v0.1.0")
    _commit(
        repo,
        ("alpha", "zeta", "gamma"),
        version="0.2.0",
        changelog=_breaking("beta", "delta"),
    )

    assert _run(check, repo, capsys)[1] == (
        "- rest2_ons.beta\n"
        "- rest2_ons.delta\n"
        "+ rest2_ons.gamma\n"
        "+ rest2_ons.zeta\n"
    )


def test_main_fails_despite_a_bullet_inside_the_base_major(
    check: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(repo, ("alpha", "beta"), version="1.0.0", tag="v1.0.0")
    _commit(repo, ("alpha",), version="1.1.0", changelog=_breaking("beta"))

    code, out, _ = _run(check, repo, capsys)

    assert code == 1
    assert (
        "check_api_diff: rest2_ons.beta removed since v1.0.0 "
        "without a ### Breaking entry\n"
    ) in out


def test_main_exits_2_on_a_shallow_clone(
    check: ModuleType,
    repo: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _commit(repo, ("alpha", "beta"), tag="v0.1.0")
    _commit(repo, ("alpha",), version="0.2.0")
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{repo}", str(shallow)],
        check=True,
        capture_output=True,
    )

    assert _run(check, shallow, capsys) == (
        2,
        "",
        "check_api_diff: shallow clone; fetch the full history and tags\n",
    )


def test_main_exits_2_when_the_base_tag_has_no_package_init(
    check: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "bare")
    _git(repo, "tag", "v0.1.0")
    _commit(repo, ("alpha",), version="0.2.0")

    code, out, err = _run(check, repo, capsys)

    assert (code, out) == (2, "")
    assert err.startswith("check_api_diff: git show: ")


@pytest.mark.parametrize(
    ("source", "reason"),
    [
        ("x = 1\n", "no module-level __all__ assignment"),
        ("__all__ = [*OTHER]\n", "__all__ is not a literal"),
        ("def (\n", "invalid syntax"),
    ],
    ids=["missing", "non-literal", "syntax-error"],
)
def test_main_exits_2_when_the_working_tree_surface_cannot_be_parsed(
    check: ModuleType,
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    source: str,
    reason: str,
) -> None:
    _commit(repo, ("alpha",), tag="v0.1.0")
    _commit(repo, source, version="0.2.0")

    code, out, err = _run(check, repo, capsys)

    assert (code, out) == (2, "")
    assert err.startswith(f"check_api_diff: {reason}")


def test_main_exits_2_when_git_times_out(
    check: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    def hang(*args: Any, **kwargs: Any) -> None:
        raise subprocess.TimeoutExpired("git", 60)

    monkeypatch.setattr(check.subprocess, "run", hang)

    code, out, err = _run(check, tmp_path, capsys)

    assert (code, out) == (2, "")
    assert "timed out" in err
