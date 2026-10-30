# Soly event data contract v1

This is the authoritative specification for **Simulator/JSONL replay → Ingestion →
Kafka → Processing**. The artifacts in [`contracts/v1/`](../contracts/v1/) are
normative together with the semantic rules below. Examples are synthetic contract
expectations, **not evidence of an implemented or executed pipeline**.

## Responsibilities and boundaries

| Component | Responsibility |
|---|---|
| Simulator / source adapter | Emit raw state strings with source timestamps; explicitly identify snapshots and changes, or supply legacy replay metadata. |
| Ingestion | Validate structure, timestamp and configured entity mapping; add the trusted installation ID and Kafka envelope; canonicalize time; generate ticks. |
| Processing | Validate Kafka envelope/key, recognize v1, interpret numeric states and validity, normalize units/signs, order open event-time groups, integrate energy and diagnose conflicts/late data. |

No service implementation, runtime schema loader, Kafka client behavior, Flink
watermark algorithm, database schema or shared Python package is introduced here.
The Python helpers under `tests/` are bounded offline contract oracles only.

## Wire formats

JSON Schema **Draft 2020-12** is used. Each schema is self-contained and requires
no HTTP references. All object variants reject unknown fields, including fields
belonging to a different event variant. All identifiers (`installation_id`,
`entity_id`) are nonempty strings without whitespace; they are opaque and
case-sensitive. No trimming or case conversion is performed. A `state` is any JSON
string, including `"0"`, `"unknown"`, `"unavailable"`, `""` or an invalid numeric string.
JSON numbers and `null` are forbidden as state values.

### Raw measurements

[`raw-event.schema.json`](../contracts/v1/raw-event.schema.json) permits exactly:

| Variant | Required fields | Forbidden among the other listed fields |
|---|---|---|
| Legacy | `entity_id`, `state`, `ts` | `measurement_kind`, `valid_from` |
| Change | `entity_id`, `state`, `ts`, `measurement_kind: "change"` | `valid_from` |
| Snapshot | `entity_id`, `state`, `ts`, `measurement_kind: "snapshot"`, `valid_from` | — |

Raw input never supplies `installation_id`, `schema_version` or `event_type`.
Such input is rejected, even if the supplied installation matches configuration;
an untrusted contradictory ID can therefore never silently override configuration.
Ticks are created by Ingestion and have no raw input variant.

The existing three-field JSONL format is structurally valid without modification.
Its measurement kind cannot be inferred from the record itself. Replay enrichment
therefore requires a sidecar conforming to `replay-metadata.schema.json`:

```json
{
  "schema_version": 1,
  "snapshot_lines": [1, 2, 3, 4, 5, 6, 7, 8],
  "snapshot_valid_from": "2026-10-04T22:00:00Z",
  "remaining_measurement_kind": "change"
}
```

Line numbers are distinct positive **one-based physical JSONL line numbers**.
Blank or malformed lines are errors, not silently skipped. Every listed line must
exist and be a legacy record. Unlisted legacy records are changes. Explicit raw
records carry their own kind/boundary and must not be listed in `snapshot_lines`.
Metadata is validated before replay; range/existence checks are also required
before a run is accepted as successful. An empty snapshot list explicitly declares
an all-change legacy file. Do not infer snapshots from equal timestamps or
hardcode "the first eight" for arbitrary files. The known historical export uses
the explicit eight-line declaration above; no private source file is published.

### Kafka payload and key

[`kafka-event.schema.json`](../contracts/v1/kafka-event.schema.json) defines:

| Variant | Required fields |
|---|---|
| Measurement change | `schema_version: 1`, `event_type: "measurement"`, `installation_id`, `entity_id`, `state`, `ts`, `measurement_kind: "change"` |
| Measurement snapshot | Same envelope, `measurement_kind: "snapshot"`, plus `valid_from` |
| Tick | Only `schema_version: 1`, `event_type: "tick"`, `installation_id`, `ts` |

`schema_version` is a JSON integer with value 1; booleans are not integers.
`valid_from` is forbidden on changes and ticks. Ticks have no sensor fields.
No additional fields, null variants or alternative type names are supported.

Payload is one UTF-8 JSON object; the Kafka key is exactly the UTF-8 bytes of the
payload's `installation_id` (not JSON-quoted). Missing keys, invalid UTF-8, a
non-object payload or key/payload disagreement are structural transport errors.
JSON object field order is irrelevant. Duplicate JSON member names and non-JSON
numeric constants such as bare `NaN` are rejected by parsers, rather than resolved
using a last-member-wins policy. These differ from the permitted string `"NaN"`.

Within one operating mode, measurements and ticks share one configurable topic
and use the same installation key. Kafka preserves a partition log order; it
does **not** guarantee event-time sorting. Live, historical replay and simulator
test runs use separate topics or fully separate environments. Repeated test runs
must also isolate/reset their downstream state and results. An installation key
alone is not sufficient run isolation. No topic name or partition count is fixed
by v1.

## Time and snapshot validity

Raw time fields use `YYYY-MM-DDTHH:MM:SS[.fraction](Z|±HH:MM)` with 1–6 fractional
digits when a fraction is present. Uppercase `T`/`Z`, seconds and explicit offsets
are required. Year range is 0001–9999. Invalid calendar dates, naive timestamps,
leap seconds, `-00:00` (unknown offset), invalid offsets and precision beyond six
digits are rejected. UTC conversion must remain within this year range.

Kafka uses **`YYYY-MM-DDTHH:MM:SS.ffffffZ`** for both `ts` and `valid_from`.
For example, `2026-10-06T12:59:57.918502+02:00` becomes
`2026-10-06T10:59:57.918502Z`. The instant and microseconds are preserved exactly;
do not pass through floating-point epoch seconds or truncate to milliseconds.
Replay speed, receive time and retry time never replace a source measurement time.

For a **change**, the effective validity time is `ts`. For a **snapshot**, `ts`
retains the source's last-known timestamp and `valid_from` declares when the
snapshot becomes usable. `valid_from >= ts` is required, compared as instants.
For live initialization/reconnection it is the observation time; for historical
initialization it is the declared replay start. A snapshot must never silently
backfill the interval between its historical source time and its observation.
If the source cannot provide a trustworthy timestamp, the adapter must diagnose
that limitation instead of inventing a historical measurement time.

The eight historical initial states describe the state at the export boundary;
they do not prove eight physical changes there. No value may be integrated before
its effective validity time. Reconnection snapshots likewise do not repair an
unobserved outage interval. Source connection monitoring and outage-quality rules
belong to later service work. There is no automatic stale-value timeout in v1.

## Repetitions, simultaneous values and closed time

Group measurement candidates by **installation, entity and effective validity
time**, using exact microseconds. A change uses `ts`; a snapshot uses `valid_from`.
For open event-time groups:

1. Repetitions of the same raw state have one state effect; retry/replay must
   preserve the original timestamp, state and snapshot boundary.
2. More than one distinct raw state in a group means `conflict`: none wins by
   Kafka arrival order, lexical ordering or last-write-wins. Even `"0"` versus
   `"0.0"` conflicts, because v1 compares unchanged raw strings.
3. A conflict makes that sensor invalid from this effective time until its next
   unambiguous state. Repeating one of the conflicting values does not resolve it.
4. Sensors at the same effective time update together; do not create artificial
   time intervals between their updates. Installations remain independent.
5. Different effective times are distinct, even if two snapshots retain the same
   old source `ts`. Changes sharing one `ts` are grouped; snapshots at one
   `valid_from` are grouped, including collisions with changes at that instant.

These rules are order-independent only within the still-open event-time region.
Events affecting already finalized time are counted/diagnosed as late and do not
rewrite finalized intervals. Reference sequences cover duplicate, conflict,
recovery, simultaneous-sensor, snapshot and microsecond cases. They are not a
checkpoint-aware streaming implementation. No event ID or sequence number is
required for this grouping, and no end-to-end exactly-once guarantee is claimed.

## Ticks and finite replay

Ticks occur every **10 seconds on the UTC raster**, with seconds divisible by ten
and zero fractional seconds. Live ticks follow real time; replay ticks follow the
virtual event clock, regardless of playback speed. A tick is not a measurement,
does not renew any sensor state, and does not confirm source availability.

Each replay declares a half-open evaluation range `[start, end)`. Initialization
snapshots begin at start. No measurements are fabricated beyond the range. Only
windows fully inside the range count as complete. A trailing partial window or
calendar day remains partial.

After the last input, additional **ticks only** may advance event time until the
actual watermark reaches the end of the last complete evaluation window. The
initial 30-second disorder tolerance means a tick at a window's end need not close
that window. `examples/replay-drain.json` illustrates a bounded-out-of-orderness
watermark `max_timestamp - 30s - 1ms`; equality at `end + 30s` is insufficient in
this example. This formula is an illustrative oracle, not a prescribed Flink
implementation. The eventual job must observe actual watermark progress across
active partitions and idle detection. Tick drain never extends evaluation bounds
or creates sensor coverage beyond the observed dataset.

## Sensor catalog and semantic errors

`sensor-catalog.json` defines eight logical roles and is checked against its
versioned schema. Entity-to-role bindings are installation-specific; the synthetic
profile example is checked against `sensor-profile.schema.json` and semantic
uniqueness/completeness rules.

| Role | Required in source profile | Purpose | Source → processing unit | Sign |
|---|---|---|---|---|
| `pv` | yes | Balance core | kW → W | nonnegative generation |
| `grid` | yes | Balance core | kW → W | positive import, negative export |
| `battery_net` | yes | Balance core | W → W | positive charging, negative discharging |
| `soc_1`, `soc_2` | yes | Context, not necessary for the power balance | % → % | 0–100 |
| `shelly_1`, `shelly_2` | no | Optional individual battery diagnostics | W → W | positive charging, negative discharging |
| `wallbox` | no | Optional vehicle charging | W → W | nonnegative consumption |

Each role maps to at most one entity, and each entity has exactly one role. The
five non-optional roles must be declared in a source profile; that does **not**
assert that all five have valid values at every instant. Missing core values make
the power balance incomplete; SOC is additional context. Optional roles can be
omitted entirely. The mirrored total battery value must be bound only once, never
summed twice or confused with per-device unsigned values. House consumption is
derived as `PV + grid - battery_net`, not assigned another measured core role.

Unknown entity bindings are rejected by Ingestion. The transport model never
converts units or adds a per-message unit override. Processing parses numeric
strings, checks finiteness/ranges/plausibility, converts kW to W, and integrates
energy. `unknown`, `unavailable`, empty strings, `NaN`, infinities and unparsable
strings are semantic invalid states. Previous valid values may be retained for
diagnosis but must not silently fill an explicitly invalid state as valid data.
Invalid or missing values never become zero; `"0"` is valid zero power.

### Diagnosis policy

The future implementations must produce a bounded diagnostic with an error code,
source location (JSONL line or Kafka topic/partition/offset) and relevant field
pointer; do not log complete private payloads or credentials.

| Error | Offline check / future behavior |
|---|---|
| Schema violation, malformed UTF-8/JSON, unknown version/type | Structural rejection; examples name schema keyword and JSON pointer. |
| `SNAPSHOT_BOUNDARY`, `TICK_GRID`, `KEY_MISMATCH` | Structural/semantic envelope rejection with field pointer. |
| `REPLAY_METADATA_REQUIRED`, invalid/out-of-range replay declaration | Replay fails rather than guessing provenance. |
| `UNKNOWN_ENTITY`, `DUPLICATE_ROLE`, `MISSING_ROLE` | Reject unconfigured entities or invalid source profiles. |
| Nonnumeric state / unavailable / unknown / conflict | Transport remains valid; Processing marks affected sensor invalid and records quality. |
| Event affecting finalized time | Late-event diagnostic; no historical correction. |

Replay stops on a structurally invalid record; live Ingestion and Processing
discard the invalid message and increment an error counter. Invalid source
configuration fails startup. These are required future behaviors, not handlers
implemented by SOLY-14. No dead-letter topic, persistence backend or automatic
retry policy is introduced.

## Verification and reproducible service copies

From an independent main-repository checkout, Python **3.12.15**:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes --only-binary=:all: -r requirements/dev.txt
python -m pip check
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy tests
```

On Windows use `py -3.12 -m venv .venv` and `.\.venv\Scripts\Activate.ps1`.
No package installation of Soly itself is needed. The default test suite needs no
submodules, network, Kafka, Flink, PostgreSQL, Home Assistant or credentials after
dependency installation. JSON Schema `format` checking is explicitly activated
with `FormatChecker` and the pinned RFC3339 validator. Calendar correctness,
microsecond precision and cross-field/key/sequence rules are actually tested.
The JSON fixture index records the intended reason and field for every negative
case. A test accounts for every published schema/example file.

Direct check dependencies are pinned in `requirements/dev.in`; the complete
transitive lock includes hashes. To regenerate using Python 3.12.15 and a separate
lock environment with **pip-tools 7.5.2**:

```bash
python -m piptools compile --generate-hashes --allow-unsafe --strip-extras --output-file requirements/dev.txt requirements/dev.in
```

Existing pins are retained unless deliberately upgraded. Verify a fresh install
and rerun checks after updating. CI uses the same commands and pinned Actions,
on every push and pull requests to `main`, with `contents: read` only.

Each independent service contains `contracts/v1/` byte-for-byte and
`contracts/provenance.json` with `schema_version`, `repository`, the full published
main-repository `commit`, and the SHA-256 of every artifact relative to the service
root. The manifest is outside the copied directory to avoid self-hashing. Its
README states the supported version, role and immutable specification URL.
Service startup/build does not fetch schemas or import neighboring submodules.

First publish the central artifacts, then pin and merge the three service copies,
then integrate their merged commits in the main repository. The final main CI
additionally checks exact file sets, hashes and source-commit provenance with
initialized submodules; the standalone contract job remains independent.

Run that separate integration check from a checkout with initialized submodules
and full main-repository history (use `git fetch --unshallow` for a shallow clone):

```bash
python -m pytest -m service_copies
```

It also tests that missing/extra files, content drift, wrong hashes, invalid source
commits and missing immutable README links are rejected. CI uses a separate
`service-copies` job with full history and recursive submodule checkout.

## Versioning and changes

Published v1 schema, catalog, semantic examples and interpretation are immutable.
New fields (even optional), types, allowed values, role/unit semantics or behavior
changes require a new integer contract version and a new directory. Unknown
versions are rejected explicitly; there is no fallback to v1 or mutable `main`
download. Documentation spelling/clarity fixes that preserve meaning may stay v1.

A contract-change issue must describe producer/consumer compatibility and migration
order, publish new schemas/examples/tests, and update service pins deliberately.
Deploy compatible consumers before enabling a new producer version; any temporary
multi-version support must be explicit. Schema registry, separate contract repo
and a shared Python runtime library remain outside this step.
