#!/bin/bash
set -euo pipefail

topic=${SOLY_KAFKA_TOPIC:?SOLY_KAFKA_TOPIC is required}
partitions=${SOLY_KAFKA_PARTITIONS:?SOLY_KAFKA_PARTITIONS is required}
if [[ ! $topic =~ ^[a-zA-Z0-9._-]+$ || $topic == . || $topic == .. || ${#topic} -gt 249 ]]; then
    echo 'Invalid SOLY_KAFKA_TOPIC.' >&2
    exit 1
fi
if [[ ! $partitions =~ ^[1-9][0-9]*$ ]]; then
    echo 'SOLY_KAFKA_PARTITIONS must be a positive integer.' >&2
    exit 1
fi
cli=/opt/kafka/bin/kafka-topics.sh
"$cli" --bootstrap-server kafka:19092 --create --if-not-exists \
    --topic "$topic" --partitions "$partitions" --replication-factor 1
description=$("$cli" --bootstrap-server kafka:19092 --describe --topic "$topic")
printf '%s\n' "$description"
if ! grep -Eq "PartitionCount:[[:space:]]*$partitions([[:space:]]|$)" <<< "$description" \
    || ! grep -Eq 'ReplicationFactor:[[:space:]]*1([[:space:]]|$)' <<< "$description"; then
    echo 'Existing topic differs from requested partitions/replication. Choose a new topic or reset explicitly.' >&2
    exit 1
fi
