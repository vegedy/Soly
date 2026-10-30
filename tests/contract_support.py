"""Small offline reference checks; no I/O adapters or processing implementation."""

import json
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "v1"
SCHEMAS = {
    "raw": "raw-event.schema.json",
    "kafka": "kafka-event.schema.json",
    "metadata": "replay-metadata.schema.json",
    "profile": "sensor-profile.schema.json",
    "catalog": "sensor-catalog.schema.json",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validator(contract: str) -> Draft202012Validator:
    return Draft202012Validator(
        load(CONTRACT / SCHEMAS[contract]), format_checker=FormatChecker()
    )


def instant(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def canonical(value: str) -> str:
    return instant(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


class ContractError(ValueError):
    def __init__(self, code: str, pointer: str) -> None:
        self.code = code
        self.pointer = pointer
        super().__init__(f"{code} at {pointer or '/'}")


def check_event(contract: str, event: dict[str, Any], key: bytes | None = None) -> None:
    validator(contract).validate(event)
    for field in ("ts", "valid_from"):
        if field in event:
            try:
                instant(event[field])
            except (ValueError, OverflowError) as error:
                raise ContractError("TIME_RANGE", "/" + field) from error
    if event.get("measurement_kind") == "snapshot":
        if instant(event["valid_from"]) < instant(event["ts"]):
            raise ContractError("SNAPSHOT_BOUNDARY", "/valid_from")
    if event.get("event_type") == "tick":
        ts = instant(event["ts"])
        if ts.second % 10 or ts.microsecond:
            raise ContractError("TICK_GRID", "/ts")
    if contract == "kafka" and key is not None:
        if key != event["installation_id"].encode("utf-8"):
            raise ContractError("KEY_MISMATCH", "/installation_id")


def check_message(key: bytes | None, payload: bytes) -> dict[str, Any]:
    """Verify fixture wire bytes, including errors hidden by permissive JSON parsers."""
    if key is None:
        raise ContractError("KEY_REQUIRED", "/installation_id")

    def members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in pairs:
            if name in result:
                raise ValueError("duplicate member")
            result[name] = value
        return result

    def constant(value: str) -> None:
        raise ValueError("non-JSON constant: " + value)

    try:
        key.decode("utf-8")
        event = json.loads(
            payload.decode("utf-8"), object_pairs_hook=members, parse_constant=constant
        )
    except (ValueError, UnicodeError) as error:
        raise ContractError("INVALID_JSON_OR_UTF8", "") from error
    if not isinstance(event, dict):
        raise ContractError("JSON_OBJECT_REQUIRED", "")
    check_event("kafka", event, key)
    return event


def check_profile(profile: dict[str, Any]) -> None:
    validator("profile").validate(profile)
    roles = list(profile["entities"].values())
    if len(roles) != len(set(roles)):
        raise ContractError("DUPLICATE_ROLE", "/entities")
    required = {"pv", "grid", "battery_net", "soc_1", "soc_2"}
    if not required.issubset(roles):
        raise ContractError("MISSING_ROLE", "/entities")


def check_replay_metadata(
    records: list[dict[str, Any]], metadata: dict[str, Any]
) -> None:
    validator("metadata").validate(metadata)
    for line in metadata["snapshot_lines"]:
        if line > len(records):
            raise ContractError("REPLAY_LINE_RANGE", "/snapshot_lines")
        if "measurement_kind" in records[line - 1]:
            raise ContractError("REPLAY_EXPLICIT_LINE", "/snapshot_lines")
    for line, raw in enumerate(records, 1):
        check_event("raw", raw)
        if line in metadata["snapshot_lines"]:
            if instant(metadata["snapshot_valid_from"]) < instant(raw["ts"]):
                raise ContractError("SNAPSHOT_BOUNDARY", "/snapshot_valid_from")


def enrich(
    raw: dict[str, Any],
    profile: dict[str, Any],
    *,
    line: int = 1,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Expected enrichment for fixtures only; never imported by a service."""
    check_event("raw", raw)
    check_profile(profile)
    if raw["entity_id"] not in profile["entities"]:
        raise ContractError("UNKNOWN_ENTITY", "/entity_id")
    payload = dict(raw)
    if "measurement_kind" not in raw:
        if metadata is None:
            raise ContractError("REPLAY_METADATA_REQUIRED", "")
        validator("metadata").validate(metadata)
        if line in metadata["snapshot_lines"]:
            payload["measurement_kind"] = "snapshot"
            payload["valid_from"] = metadata["snapshot_valid_from"]
        else:
            payload["measurement_kind"] = metadata["remaining_measurement_kind"]
    payload.update(
        schema_version=1,
        event_type="measurement",
        installation_id=profile["installation_id"],
        ts=canonical(payload["ts"]),
    )
    if "valid_from" in payload:
        payload["valid_from"] = canonical(payload["valid_from"])
    key = profile["installation_id"]
    check_event("kafka", payload, key.encode("utf-8"))
    return {"key": key, "payload": payload}


def transitions(
    events: list[dict[str, Any]], *, finalized_before: str | None = None
) -> list[dict[str, Any]]:
    """Set-based oracle for open event-time groups, not a stream processor."""
    groups: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for event in events:
        check_event("kafka", event)
        if event["event_type"] == "tick":
            continue
        effective = event.get("valid_from", event["ts"])
        if finalized_before is not None and instant(effective) < instant(
            finalized_before
        ):
            continue
        groups[
            (canonical(effective), event["installation_id"], event["entity_id"])
        ].add(event["state"])
    result = []
    for (at, installation, entity), states in sorted(groups.items()):
        state = next(iter(states)) if len(states) == 1 else None
        quality = "conflict" if state is None else "valid"
        if state is not None:
            try:
                if not Decimal(state).is_finite():
                    quality = "invalid"
            except InvalidOperation:
                quality = "invalid"
        result.append(
            dict(
                installation_id=installation,
                at=at,
                entity_id=entity,
                state=state,
                quality=quality,
            )
        )
    return result
