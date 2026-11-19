"""Keep standalone development tools in sync without runtime cross-repo imports."""

import shutil
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


def verify_development_copy(service: Path, name: str) -> None:
    for relative in SHARED_FILES:
        path = service / relative
        assert path.is_file() and not path.is_symlink(), f"{path}: missing or symlink"
        actual = path.read_bytes()
        expected = (ROOT / relative).read_bytes()
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
        shutil.copyfile(ROOT / shared, target)
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
        shutil.copyfile(ROOT / shared, target)
    with pytest.raises(AssertionError, match="unexpected project identity"):
        verify_development_copy(tmp_path, "simulator")
