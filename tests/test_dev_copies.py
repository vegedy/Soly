"""Keep standalone development tools in sync without runtime cross-repo imports."""

import re
from pathlib import Path

import pytest

from tests.contract_support import ROOT

pytestmark = pytest.mark.service_copies
SHARED_FILES = (
    "dev.sh",
    "dev.ps1",
    "scripts/__init__.py",
    "scripts/dev.py",
    "tests/test_dev.py",
    ".gitattributes",
)
MAIN_ONLY_BLOCKS = {"dev.sh": 1, "dev.ps1": 1, "scripts/dev.py": 2}


def shared_bytes(relative: str) -> bytes:
    data = (ROOT / relative).read_bytes()
    pattern = rb"(?m)^[ \t]*# BEGIN SOLY MAIN-ONLY STACK\n(?s:.*?)^[ \t]*# END SOLY MAIN-ONLY STACK\n"
    data, count = re.subn(pattern, b"", data)
    assert count == MAIN_ONLY_BLOCKS.get(relative, 0), "unexpected main-only blocks"
    assert b"SOLY MAIN-ONLY STACK" not in data, "malformed main-only block"
    return data


def verify_development_copy(service: Path, name: str) -> None:
    for relative in SHARED_FILES:
        path = service / relative
        assert path.is_file() and not path.is_symlink(), f"{path}: missing or symlink"
        actual = path.read_bytes()
        expected = shared_bytes(relative)
        if relative == "scripts/dev.py":
            identity = f'PROJECT = "soly-{name}"\n'.encode()
            assert actual.count(identity) == 1, f"{path}: unexpected project identity"
            actual = actual.replace(identity, b'PROJECT = "soly"\n', 1)
        assert actual == expected, f"{path}: shared development tool differs"


@pytest.mark.parametrize("name", ["simulator", "ingestion", "processing"])
def test_integrated_development_copy(name: str) -> None:
    verify_development_copy(ROOT / name, name)


@pytest.mark.parametrize("relative", SHARED_FILES)
def test_development_verification_rejects_drift(tmp_path: Path, relative: str) -> None:
    for shared in SHARED_FILES:
        target = tmp_path / shared
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(shared_bytes(shared))
    driver = tmp_path / "scripts/dev.py"
    driver.write_bytes(
        driver.read_bytes().replace(
            b'PROJECT = "soly"\n', b'PROJECT = "soly-simulator"\n'
        )
    )
    verify_development_copy(tmp_path, "simulator")
    path = tmp_path / relative
    path.write_bytes(path.read_bytes() + b"\n# drift\n")
    with pytest.raises(AssertionError, match="differs"):
        verify_development_copy(tmp_path, "simulator")


def test_development_verification_rejects_wrong_identity(tmp_path: Path) -> None:
    for shared in SHARED_FILES:
        target = tmp_path / shared
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(shared_bytes(shared))
    with pytest.raises(AssertionError, match="unexpected project identity"):
        verify_development_copy(tmp_path, "simulator")


def test_service_cannot_hide_drift_in_main_only_markers(tmp_path: Path) -> None:
    for shared in SHARED_FILES:
        target = tmp_path / shared
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(shared_bytes(shared))
    driver = tmp_path / "scripts/dev.py"
    driver.write_bytes(
        driver.read_bytes().replace(
            b'PROJECT = "soly"\n', b'PROJECT = "soly-simulator"\n'
        )
    )
    script = tmp_path / "dev.sh"
    script.write_bytes(
        script.read_bytes()
        + b"# BEGIN SOLY MAIN-ONLY STACK\nexit 0\n# END SOLY MAIN-ONLY STACK\n"
    )
    with pytest.raises(AssertionError, match="differs"):
        verify_development_copy(tmp_path, "simulator")
