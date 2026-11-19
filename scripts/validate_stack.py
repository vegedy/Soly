"""Destructive acceptance test, restricted to a new soly19-validation-* project."""

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

if __name__ == "__main__" and not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.stack import ROOT, Stack, StackError  # noqa: E402


def validate(instance: Stack) -> None:
    if not instance.project.startswith("soly19-validation-"):
        raise StackError("Validation requires its own soly19-validation-* project.")
    existing = instance.call(
        [
            instance.docker,
            "ps",
            "--all",
            "--quiet",
            "--filter",
            f"label=com.docker.compose.project={instance.project}",
        ]
    ).stdout.strip()
    volumes = instance.call(
        [
            instance.docker,
            "volume",
            "ls",
            "--quiet",
            "--filter",
            f"label=com.docker.compose.project={instance.project}",
        ]
    ).stdout.strip()
    if existing or volumes:
        raise StackError(
            "Validation refuses an existing project or data volumes. Choose a fresh name."
        )
    token = uuid.uuid4().hex
    topic = f"soly-persistence-{token}"
    table = f"soly_infra_probe_{token}"
    try:
        instance.up()
        instance.smoke()
        instance.kafka(
            "kafka-topics",
            "--create",
            "--topic",
            topic,
            "--partitions",
            "1",
            "--replication-factor",
            "1",
        )
        instance.kafka(
            "kafka-console-producer", "--topic", topic, input_text=token + "\n"
        )
        instance.sql(
            f"CREATE TABLE {table} (value text); INSERT INTO {table} VALUES ('{token}');\n"
        )
        instance.initialize_topic()
        # A mismatched existing topic must fail, preserving it and its messages.
        partitions = int(
            instance.config["services"]["kafka-init"]["environment"][
                "SOLY_KAFKA_PARTITIONS"
            ]
        )
        try:
            instance.compose(
                "run",
                "--rm",
                "--no-deps",
                "-e",
                f"SOLY_KAFKA_PARTITIONS={partitions + 1}",
                "kafka-init",
            )
        except subprocess.CalledProcessError:
            print("Expected topic mismatch was rejected.", flush=True)
        else:
            raise StackError("Existing topic mismatch unexpectedly succeeded.")
        instance.up()
        instance.down()
        instance.up()
        if instance.sql(f"SELECT value FROM {table};\n") != token:
            raise StackError("PostgreSQL probe did not survive down/up.")
        actual = instance.kafka(
            "kafka-console-consumer",
            "--topic",
            topic,
            "--from-beginning",
            "--max-messages",
            "1",
            "--timeout-ms",
            "30000",
        ).strip()
        if actual != token:
            raise StackError("Kafka probe did not survive down/up.")
        instance.status()
        for service in ("kafka", "postgres", "jobmanager", "taskmanager"):
            info = instance.inspect(service)
            print(
                json.dumps({"service": service, "image": info["Image"]}, sort_keys=True)
            )
        print(
            instance.call(
                [
                    instance.docker,
                    "stats",
                    "--no-stream",
                    "--format",
                    "{{.Name}} CPU={{.CPUPerc}} memory={{.MemUsage}}",
                    *(
                        instance.container(name)
                        for name in ("kafka", "postgres", "jobmanager", "taskmanager")
                    ),
                ]
            ).stdout
        )
        instance.down(reset=True)
        remaining = instance.call(
            [
                instance.docker,
                "volume",
                "ls",
                "--quiet",
                "--filter",
                f"label=com.docker.compose.project={instance.project}",
            ]
        ).stdout.strip()
        if remaining:
            raise StackError("Reset left project volumes behind.")
        print(
            "Acceptance OK: repeated start/init, topic mismatch, Kafka/SQL persistence, isolated reset.",
            flush=True,
        )
    finally:
        # Diagnostics contain service output only, never rendered config or inspect Env.
        print(instance.compose("logs", "--no-color", "--tail", "60").stdout)
        instance.down(reset=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env.example")
    parser.add_argument("--project-name", required=True)
    args = parser.parse_args()
    try:
        validate(Stack(args.env_file, args.project_name))
    except (
        StackError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        OSError,
    ) as error:
        print(f"Acceptance failed: {type(error).__name__}", file=sys.stderr)
        if isinstance(error, StackError):
            print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
