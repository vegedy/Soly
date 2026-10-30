import copy
import itertools
import json
from datetime import timedelta
from typing import Any

import pytest
from jsonschema import Draft202012Validator, ValidationError

from tests.contract_support import (
    CONTRACT,
    SCHEMAS,
    ContractError,
    canonical,
    check_event,
    check_message,
    check_profile,
    check_replay_metadata,
    enrich,
    instant,
    load,
    transitions,
    validator,
)

CASES: list[dict[str, Any]] = load(CONTRACT / "examples/event-cases.json")
SEQUENCES: list[dict[str, Any]] = load(CONTRACT / "examples/sequences.json")


def flatten(error: ValidationError) -> list[ValidationError]:
    return [error] + [leaf for child in error.context for leaf in flatten(child)]


@pytest.mark.parametrize("name", SCHEMAS)
def test_schemas_are_valid(name: str) -> None:
    Draft202012Validator.check_schema(load(CONTRACT / SCHEMAS[name]))


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_event_cases(case: dict[str, Any]) -> None:
    event = case["event"]
    key = case.get("key")
    key_bytes = key.encode("utf-8") if key is not None else None
    if case["valid"]:
        check_event(case["contract"], event, key_bytes)
    elif "expected_keyword" in case:
        with pytest.raises(ValidationError):
            check_event(case["contract"], event, key_bytes)
        errors = [
            leaf
            for error in validator(case["contract"]).iter_errors(event)
            for leaf in flatten(error)
        ]
        assert any(
            error.validator == case["expected_keyword"]
            and "/".join([""] + [str(part) for part in error.absolute_path]).rstrip("/")
            == case["expected_pointer"]
            for error in errors
        ), case["reason"]
    else:
        with pytest.raises(ContractError) as caught:
            check_event(case["contract"], event, key_bytes)
        assert caught.value.code == case["expected_code"]
        assert caught.value.pointer == case["expected_pointer"]


def test_format_validation_is_active_without_pattern_help() -> None:
    v = Draft202012Validator(
        {"type": "string", "format": "date-time"},
        format_checker=validator("raw").format_checker,
    )
    with pytest.raises(ValidationError, match="date-time"):
        v.validate("2026-02-30T11:00:00Z")


def test_offsets_preserve_microseconds_and_raw_state() -> None:
    assert canonical("2026-10-06T12:59:57.918502+02:00") == (
        "2026-10-06T10:59:57.918502Z"
    )
    assert canonical("2026-10-06T05:30:00.123456-05:30") == (
        "2026-10-06T11:00:00.123456Z"
    )
    assert canonical("2026-10-06T11:00:00.000001Z") != canonical(
        "2026-10-06T11:00:00.000002Z"
    )
    fixture = load(CONTRACT / "examples/enrichment.json")
    for record in fixture["records"]:
        before = copy.deepcopy(record["raw"])
        actual = enrich(
            record["raw"],
            fixture["configuration"],
            line=record["line"],
            metadata=fixture["metadata"],
        )
        assert actual == record["expected"]
        assert actual["payload"]["state"] == before["state"]
        assert record["raw"] == before


def test_explicit_events_need_no_legacy_metadata() -> None:
    fixture = load(CONTRACT / "examples/enrichment.json")
    raw = dict(fixture["records"][1]["raw"], measurement_kind="change")
    assert enrich(raw, fixture["configuration"]) == fixture["records"][1]["expected"]


def test_legacy_requires_declared_metadata_and_known_sensor() -> None:
    fixture = load(CONTRACT / "examples/enrichment.json")
    raw = fixture["records"][0]["raw"]
    with pytest.raises(ContractError, match="REPLAY_METADATA_REQUIRED"):
        enrich(raw, fixture["configuration"])
    with pytest.raises(ContractError, match="UNKNOWN_ENTITY"):
        enrich(dict(raw, entity_id="sensor.not_configured"), fixture["configuration"])


def test_replay_metadata_must_describe_existing_legacy_records() -> None:
    fixture = load(CONTRACT / "examples/enrichment.json")
    records = [row["raw"] for row in fixture["records"]]
    metadata = fixture["metadata"]
    check_replay_metadata(records, metadata)
    with pytest.raises(ContractError, match="REPLAY_LINE_RANGE"):
        check_replay_metadata(records, dict(metadata, snapshot_lines=[3]))
    explicit = [dict(records[0], measurement_kind="change"), records[1]]
    with pytest.raises(ContractError, match="REPLAY_EXPLICIT_LINE"):
        check_replay_metadata(explicit, metadata)
    with pytest.raises(ContractError, match="SNAPSHOT_BOUNDARY"):
        check_replay_metadata(
            records, dict(metadata, snapshot_valid_from="2026-10-06T00:00:00Z")
        )


def test_utc_conversion_rejects_year_overflow() -> None:
    event = dict(entity_id="sensor.demo_pv", state="0", ts="0001-01-01T00:00:00+01:00")
    with pytest.raises(ContractError, match="TIME_RANGE"):
        check_event("raw", event)


def test_profiles_and_catalog() -> None:
    profile = load(CONTRACT / "examples/sensor-profile.json")
    check_profile(profile)
    catalog = load(CONTRACT / "sensor-catalog.json")
    validator("catalog").validate(catalog)
    assert len({row["role"] for row in catalog["roles"]}) == 8
    assert {
        row["role"] for row in catalog["roles"] if row["requirement"] == "balance_core"
    } == {"pv", "grid", "battery_net"}
    duplicate = copy.deepcopy(profile)
    duplicate["entities"]["sensor.demo_soc_2"] = "battery_net"
    with pytest.raises(ContractError, match="DUPLICATE_ROLE"):
        check_profile(duplicate)
    missing = copy.deepcopy(profile)
    del missing["entities"]["sensor.demo_soc_2"]
    with pytest.raises(ContractError, match="MISSING_ROLE"):
        check_profile(missing)
    minimal = copy.deepcopy(profile)
    minimal["entities"] = {
        entity: role
        for entity, role in profile["entities"].items()
        if role not in {"shelly_1", "shelly_2", "wallbox"}
    }
    check_profile(minimal)


@pytest.mark.parametrize("sequence", SEQUENCES, ids=[row["name"] for row in SEQUENCES])
def test_sequences_are_order_independent(sequence: dict[str, Any]) -> None:
    for permutation in itertools.permutations(sequence["events"]):
        assert transitions(list(permutation)) == sequence["expected"]


def test_installations_are_independent_and_key_is_utf8() -> None:
    event = next(row["event"] for row in CASES if row["name"] == "measurement")
    other = dict(event, installation_id="démonstration", state="100")
    check_event("kafka", other, "démonstration".encode())
    with pytest.raises(ContractError, match="KEY_MISMATCH"):
        check_event("kafka", other, b"\xff")
    assert len(transitions([event, other])) == 2


def test_wire_json_is_strict_and_key_is_required() -> None:
    event = next(row["event"] for row in CASES if row["name"] == "measurement")
    payload = json.dumps(event).encode()
    assert check_message(b"demo_001", payload) == event
    with pytest.raises(ContractError, match="KEY_REQUIRED"):
        check_message(None, payload)
    for bad in [b"\xff", b'{"state":"1","state":"2"}', b'{"state":NaN}', b"{"]:
        with pytest.raises(ContractError, match="INVALID_JSON_OR_UTF8"):
            check_message(b"demo_001", bad)
    with pytest.raises(ContractError, match="INVALID_JSON_OR_UTF8"):
        check_message(b"\xff", payload)
    with pytest.raises(ContractError, match="JSON_OBJECT_REQUIRED"):
        check_message(b"demo_001", b"[]")


def test_events_before_finalized_boundary_do_not_rewrite_history() -> None:
    event = next(row["event"] for row in CASES if row["name"] == "measurement")
    closed = dict(event, ts="2026-10-06T11:00:00.000000Z", state="1")
    late_conflict = dict(closed, state="2")
    boundary = dict(event, ts="2026-10-06T11:00:10.000000Z", state="3")
    assert transitions(
        [late_conflict, boundary, closed], finalized_before=boundary["ts"]
    ) == transitions([boundary])


def test_tick_drain_closes_only_complete_evaluation_windows() -> None:
    fixture = load(CONTRACT / "examples/replay-drain.json")
    start = instant(fixture["evaluation_start"])
    end = instant(fixture["evaluation_end"])
    complete_end = instant(fixture["last_complete_window_end"])
    delta = timedelta(seconds=fixture["out_of_orderness_seconds"])
    resolution = timedelta(microseconds=fixture["watermark_resolution_microseconds"])
    for step in fixture["steps"]:
        tick = dict(
            schema_version=1,
            event_type="tick",
            installation_id="demo_001",
            ts=step["tick"],
        )
        check_event("kafka", tick)
        watermark = instant(step["tick"]) - delta - resolution
        assert (watermark >= complete_end) == step["expected_closed"]
    boundaries = []
    current = start + timedelta(seconds=10)
    while current <= end:
        boundaries.append(canonical(current.isoformat()))
        current += timedelta(seconds=10)
    assert boundaries == fixture["expected_complete_window_ends"]
    assert fixture["evaluation_end"] == "2026-10-06T11:00:25.000000Z"


def test_all_published_schemas_and_examples_are_accounted_for() -> None:
    assert {path.name for path in CONTRACT.glob("*.schema.json")} == set(
        SCHEMAS.values()
    )
    assert {path.name for path in (CONTRACT / "examples").glob("*.json")} == {
        "event-cases.json",
        "sensor-profile.json",
        "enrichment.json",
        "sequences.json",
        "replay-drain.json",
    }
