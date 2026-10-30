"""Opt-in checks for the integrated submodules; default tests stay standalone."""

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from tests.contract_support import CONTRACT, ROOT, load

REPOSITORY = "https://github.com/vegedy/Soly"
pytestmark = pytest.mark.service_copies


def verify_copy(service: Path) -> None:
    manifest: dict[str, Any] = load(service / "contracts/provenance.json")
    schema = {
        "type": "object",
        "required": ["schema_version", "repository", "commit", "sha256"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "repository": {"const": REPOSITORY},
            "commit": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
            "sha256": {
                "type": "object",
                "additionalProperties": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            },
        },
    }
    Draft202012Validator(schema).validate(manifest)
    commit = manifest["commit"]
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    expected = {
        path.relative_to(ROOT).as_posix(): path
        for path in CONTRACT.rglob("*")
        if path.is_file()
    }
    actual = {
        path.relative_to(service).as_posix()
        for path in (service / "contracts/v1").rglob("*")
        if path.is_file()
    }
    assert not any(path.is_symlink() for path in (service / "contracts/v1").rglob("*"))
    assert actual == set(expected) == set(manifest["sha256"]), (
        "artifact file set differs"
    )
    assert (
        subprocess.check_output(["git", "cat-file", "-t", commit], cwd=ROOT).strip()
        == b"commit"
    )
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT, check=True
    )
    for relative, original in expected.items():
        copied = service / relative
        assert not copied.is_symlink(), relative
        content = copied.read_bytes()
        assert content == original.read_bytes(), relative
        assert hashlib.sha256(content).hexdigest() == manifest["sha256"][relative], (
            relative
        )
        published = subprocess.check_output(
            ["git", "show", f"{commit}:{relative}"], cwd=ROOT
        )
        assert content == published, f"{relative}: source commit differs"
    spec = f"{REPOSITORY}/blob/{commit}/docs/data-contract.md"
    assert spec in (service / "README.md").read_text(encoding="utf-8")


@pytest.mark.service_copies
@pytest.mark.parametrize("service", ["simulator", "ingestion", "processing"])
def test_integrated_contract_copy(service: str) -> None:
    verify_copy(ROOT / service)


@pytest.mark.parametrize(
    "damage", ["content", "missing", "extra", "hash", "source", "readme"]
)
def test_copy_verification_rejects_drift(tmp_path: Path, damage: str) -> None:
    service = tmp_path / "service"
    shutil.copytree(ROOT / "simulator/contracts", service / "contracts")
    shutil.copyfile(ROOT / "simulator/README.md", service / "README.md")
    verify_copy(service)
    manifest_path = service / "contracts/provenance.json"
    manifest = load(manifest_path)
    relative = "contracts/v1/raw-event.schema.json"
    if damage == "content":
        (service / relative).write_text("{}", encoding="utf-8")
    elif damage == "missing":
        (service / relative).unlink()
    elif damage == "extra":
        (service / "contracts/v1/untracked.json").write_text("{}", encoding="utf-8")
    elif damage == "hash":
        manifest["sha256"][relative] = "0" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    elif damage == "source":
        manifest["commit"] = "0" * 40
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    else:
        (service / "README.md").write_text(
            "missing immutable reference", encoding="utf-8"
        )
    with pytest.raises((AssertionError, subprocess.CalledProcessError)):
        verify_copy(service)
