"""Executed through stdin inside each Flink role; no host or source mounts."""

import hashlib
import json
import sys
from importlib import import_module
from importlib.metadata import version
from pathlib import Path


def main() -> None:
    lock = json.loads(sys.argv[1])
    if sys.version_info[:3] != (3, 12, 15) or version("apache-flink") != "2.2.1":
        raise RuntimeError("Unexpected Python/PyFlink version")
    if Path(sys.executable).resolve() != Path("/opt/python/bin/python3").resolve():
        raise RuntimeError("Unexpected Python interpreter")
    jars = {}
    for artifact in lock["artifacts"]:
        name = Path(artifact["path"]).name
        actual = hashlib.sha256(
            (Path("/opt/flink/lib") / name).read_bytes()
        ).hexdigest()
        if actual != artifact["sha256"]:
            raise RuntimeError(f"Connector hash mismatch: {name}")
        jars[name] = actual
    # The official Flink entrypoint serializes the effective YAML configuration.
    # PyYAML is already part of the image's pinned PyFlink runtime lock.
    config = import_module("yaml").safe_load(
        Path("/opt/flink/conf/config.yaml").read_text(encoding="utf-8")
    )
    interpreter_options = {}
    for key in ("python.client.executable", "python.executable"):
        value = config.get(key)
        if value is None:
            value = config
            for part in key.split("."):
                value = value.get(part, {})
        if value != "/opt/python/bin/python3":
            raise RuntimeError(f"Unexpected effective {key}: {value}")
        interpreter_options[key] = value
    print(
        json.dumps(
            {
                "python": sys.version.split()[0],
                "pyflink": version("apache-flink"),
                "interpreter": "/opt/python/bin/python3",
                "configuration": interpreter_options,
                "jars": jars,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
