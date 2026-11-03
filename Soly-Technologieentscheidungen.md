# Soly: Technologie- und Versionsentscheidungen

- **Entscheidungsdatum:** 23. Oktober 2026
- **Geltungsbereich:** Technischer Ausgangsstand für Phase 2 des Data-Engineering-Projekts
- **Repository-Abgleich:** 2. November 2026 (SOLY-17)
- **Status:** Historische Auswahl vom 23. Oktober mit inzwischen implementierten Service-Fundamenten abgeglichen. Service-Builds und Laufzeit-Smoke-Tests sind in den Service-READMEs historisch dokumentiert; der vollständige fachliche Pipeline-Test steht aus. Der Abgleich ist kein erneuter Build- oder Kompatibilitätsnachweis.

Maßgebliche Implementierung: [Simulator-README](simulator/README.md),
[Ingestion-README](ingestion/README.md), [Processing-README](processing/README.md),
jeweilige `pyproject.toml`, `requirements/`, `Dockerfile` und
`.github/workflows/ci.yml`. Die Auswahlversionen unten werden beibehalten;
noch nicht eingesetzte Infrastruktur wird ausdrücklich als Zielstand behandelt.
[CONTRIBUTING.md](CONTRIBUTING.md) beschreibt Einrichtung und Prüfungen.
Die externen Quellen sind die Referenzen der ursprünglichen Auswahl; sie wurden
für diesen Repository-Abgleich nicht erneut recherchiert.

## 1. Projektname und Lizenz

Der Projektname lautet **Soly**. Der eigene Projektcode wird unter der **MIT-Lizenz** veröffentlicht. Beide Entscheidungen wurden vom Projektverantwortlichen vorgegeben.

Die MIT-Lizenz erlaubt eine unkomplizierte Weiterverwendung des eigenen Codes und passt zur geplanten Veröffentlichung als Portfolio-Projekt. Die Lizenzentscheidung bezieht sich auf den eigenen Code; eingebundene Bibliotheken, Laufzeiten, Containerbestandteile und Daten behalten ihre jeweiligen Lizenzbedingungen. Alle vier Repositories enthalten inzwischen eine `LICENSE`-Datei.

## 2. Entscheidungsgrundsätze

Die Versionsauswahl richtet sich nach der gemeinsamen Nutzbarkeit der gesamten Pipeline. Ausgangspunkt ist die Kombination aus Flink, PyFlink, Python, Java und den separat veröffentlichten Connectoren.

Es gelten folgende Grundsätze:

1. Flink und PyFlink verwenden dieselbe Version.
2. Die Connectoren werden für die gewählte Flink-Versionslinie ausgewählt.
3. Alle eigenen Python-Komponenten verwenden dieselbe Python-Version.
4. JobManager und TaskManager verwenden dasselbe eigene Processing-Image.
5. Abhängigkeiten und Container werden reproduzierbar festgeschrieben.
6. Dokumentierte Kompatibilität ersetzt keinen praktischen Integrationstest.

## 3. Laufzeiten und Infrastruktur

| Komponente | Entscheidung | Einsatz und Begründung |
|---|---|---|
| Python | **3.12.15** | Einheitliche Version für Simulator, Ingestion und Processing. Python 3.12 wird von PyFlink 2.2.1 unterstützt. Ein gemeinsamer Stand vereinfacht lokale Entwicklung, CI und Container-Builds. |
| Apache Flink | **2.2.1** | Zentrale Stream-Processing-Laufzeit. Für die Linie 2.2 sind passende Kafka- und JDBC-Connectoren dokumentiert. Diese zusammenpassende Kombination ist der Grund für die Wahl dieser Linie. |
| PyFlink | **2.2.1** | Python-Paket `apache-flink==2.2.1`. Gleiche Version wie die Flink-Laufzeit, um Abweichungen zwischen Python-API und JVM-Laufzeit zu vermeiden. |
| Java | **17 LTS** | Von Flink empfohlene JVM-Version. Im Processing-Basisimage per Digest fixiert; README dokumentiert Temurin 17.0.20.1+1 als historischen Laufzeitnachweis. |
| Apache Kafka | **4.2.2** | Veröffentlichter stabiler Patchstand für die Ereignispufferung. Ziel für das lokale MVP: ein Broker im KRaft-Modus ohne ZooKeeper; Broker-/Compose-Setup ist noch nicht umgesetzt. |
| PostgreSQL | **18.6** | Ausgewählter Zielstand für Energieaggregate und SQL-Views; Datenbank-/Compose-Setup steht noch aus. JDBC-Treiber siehe Abschnitt 4. |

Die Auswahl von Flink 2.2.1 bedeutet nicht, dass grundsätzlich keine neuere Flink-Version eingesetzt werden könnte. Sie legt eine konkrete Basis fest, für die die benötigten Connector-Versionen recherchiert wurden. Ein Wechsel der Flink-Linie wird als gemeinsame Änderung von Laufzeit, PyFlink und Connectoren bewertet.

Quellen:

- [Python 3.12.15: Releaseinformationen](https://www.python.org/downloads/release/python-31215/)
- [PyFlink 2.2.1: Paket und unterstützte Python-Versionen](https://pypi.org/project/apache-flink/2.2.1/)
- [Apache Flink: veröffentlichte Versionen](https://flink.apache.org/downloads/)
- [Flink 2.2: Java-Kompatibilität](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/java_compatibility/)
- [Apache Kafka: Downloads und Releaseinformationen](https://kafka.apache.org/community/downloads/)
- [PostgreSQL: unterstützte Versionen und Versionsrichtlinie](https://www.postgresql.org/support/versioning/)

## 4. Connectoren und Clients

| Komponente | Entscheidung | Einsatz und Begründung |
|---|---|---|
| Flink-Kafka-Connector | **5.0.0-2.2** | Kafka-Eingang des Processing-Jobs. Diese Version ist in der Flink-2.2-Dokumentation angegeben. |
| Flink-JDBC-Connector | **4.1.0-2.2** | PostgreSQL-Ausgang des Processing-Jobs. Diese Version ist in der Flink-2.2-Dokumentation angegeben. |
| PostgreSQL-JDBC-Treiber | **42.7.14** | Separater Datenbanktreiber für den JDBC-Connector; veröffentlichter aktueller Treiberstand zum Entscheidungszeitpunkt. |
| Python-Kafka-Client | **confluent-kafka 2.16.0** | Producer und gegebenenfalls administrativer Client der Ingestion. Der Client unterstützt Apache-Kafka-Broker; eine Confluent-Plattform wird dafür nicht benötigt. |

Die Endung **`-2.2` ist Bestandteil der Connector-Version** und bezeichnet den Build für die Flink-Linie 2.2. Die Versionsnummern der Connectoren sind unabhängig von der Flink-Versionsnummer. Insbesondere bezeichnet `5.0.0` hier die Connector-Version und nicht die Version des Kafka-Brokers.

Die JDBC-Anbindung benötigt neben dem PostgreSQL-Treiber die zur verwendeten API passenden Connector-Module und deren transitiven Abhängigkeiten. Für die modulare JDBC-Variante gehören dazu insbesondere `flink-connector-jdbc-core` und `flink-connector-jdbc-postgres` im festgelegten Versionsstand. Die Auflösung erfolgt bewusst über `processing/connectors/pom.xml`; `dependency-tree.txt` und `jars.lock.json` halten das Ergebnis einschließlich Hashes fest. Der Image-Build lädt nur die gelockten JARs und prüft ihre Hashes. Einzelne kopierte JARs ersetzen diesen Umfang nicht. Für JDBC ist die Table API gewählt; der ältere Python-DataStream-JDBC-Wrapper passt nicht zur modularen Klassenstruktur. Details und Generatorbefehle: [Processing-README](processing/README.md#jvm-abhängigkeiten-und-gewählte-api).

Der PostgreSQL-Sink soll vollständige Fensterergebnisse mittels idempotenter UPSERTs schreiben. Die bereits vorgesehene Kombination aus At-Least-Once-Schreiben und Checkpoint-Recovery bleibt bestehen. Aus der Versionswahl wird keine End-to-End-Exactly-Once-Garantie abgeleitet.

Quellen:

- [Flink 2.2: Kafka-Connector und Python-Abhängigkeiten](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/connectors/datastream/kafka/)
- [Flink 2.2: JDBC-Connector für die Table API und benötigte Module](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/connectors/table/jdbc/)
- [Flink 2.2: JDBC-Sink für die DataStream API](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/connectors/datastream/jdbc/)
- [PostgreSQL-JDBC-Treiber: Downloads](https://jdbc.postgresql.org/download/)
- [PostgreSQL-JDBC-Treiber 42.7.14: Releaseinformationen](https://jdbc.postgresql.org/changelogs/2026-10-07-42.7.14-release/)
- [confluent-kafka 2.16.0](https://pypi.org/project/confluent-kafka/2.16.0/)

## 5. Container-Strategie

| Dienst | Gewähltes Basis-Image |
|---|---|
| Simulator | `python:3.12.15-slim-bookworm` |
| Ingestion | `python:3.12.15-slim-bookworm` |
| Flink JobManager | Eigenes Processing-Image auf Basis von `flink:2.2.1-java17` |
| Flink TaskManager | Dasselbe eigene Processing-Image wie der JobManager |
| Kafka | `apache/kafka:4.2.2` |
| PostgreSQL | `postgres:18.6-bookworm` |

Für Simulator und Ingestion dient dieselbe Python-Basis als Ausgangspunkt. Dadurch bleibt die Python-Umgebung über beide Komponenten hinweg konsistent. Die Debian-Bookworm-Slim-Variante begrenzt den Umfang des Basis-Images und verwendet eine glibc-basierte Umgebung.

Das eigene Processing-Image ergänzt die offizielle Flink-Basis um **Python 3.12.15**, **PyFlink 2.2.1**, die Connectoren samt benötigten Abhängigkeiten und die Paket-/Smoke-Test-Artefakte; der fachliche Job folgt separat. Es wird nicht vorausgesetzt, dass das unveränderte Flink-Basis-Image bereits diese Python-Version enthält. Die Installation und Auswahl des Python-Interpreters werden explizit im Build und in der Flink-Konfiguration umgesetzt.

JobManager und TaskManager verwenden identische Artefakte, damit Python-Pakete und JVM-Connectoren auf beiden Rollen übereinstimmen. Die Java-Version des Kafka-Containers ist Bestandteil seines eigenen Images und muss nicht mit der JVM des Flink-Containers vereinheitlicht werden.

Die Service-Images sind inzwischen in ihren Dockerfiles per Basis-Digest fixiert.
Simulator und Ingestion verwenden denselben Python-Digest; Processing verwendet
den Flink-Digest, einen geprüften Python-Quellhash und einen datierten
Ubuntu-Paketsnapshot. Konkrete Digests und der historische JVM-Nachweis stehen in
den Service-READMEs, damit diese Werte nicht an mehreren Stellen gepflegt werden.
JobManager und TaskManager verwenden dasselbe Processing-Image und den expliziten
Python-Interpreter. Kafka und PostgreSQL sind weiterhin ausgewählte Zielstände;
ihre Infrastruktur und Digests sind noch nicht im Hauptrepo eingerichtet.
Ein Versions-Tag allein fixiert nicht alle Betriebssystempakete oder JVM-Patches.

Quellen:

- [Offizielle Python-Image-Definitionen](https://github.com/docker-library/python/blob/master/versions.json)
- [Offizielle Flink-Image-Tags](https://github.com/docker-library/official-images/blob/master/library/flink)
- [Offizielles PostgreSQL-Image](https://hub.docker.com/_/postgres)
- [Apache Kafka: veröffentlichte Docker-Images](https://kafka.apache.org/community/downloads/)

## 6. Entwicklungswerkzeuge und Python-Projektaufbau

| Werkzeug | Entscheidung | Begründung |
|---|---|---|
| pytest | **9.1.1** | Einheitlicher Test-Runner für fachliche Tests, Adaptertests und geeignete Integrationstests. |
| Ruff | **0.17.2** | Einheitliches Werkzeug für Linting und Formatierung; kein zusätzlicher Formatter ist vorgesehen. |
| mypy | **2.4.0** | Statische Typprüfung des eigenen Python-Codes. Typprüfungsregeln werden im jeweiligen Projekt konfiguriert. |
| Virtuelle Umgebung | **`venv`** | Entspricht dem vereinbarten Entwicklungsansatz; pro Python-Repository eine getrennte lokale Umgebung. |
| Projektkonfiguration | **`pyproject.toml`** | Zentraler Ort für Paketmetadaten und Werkzeugkonfiguration pro Python-Repository. |

Die Werkzeugversionen werden in allen Python-Repositories einheitlich eingesetzt. Lokale Prüfungen und CI verwenden dieselben festgeschriebenen Versionen.

Virtuelle Umgebungen werden nicht eingecheckt. Das gewählte Verfahren ist
**pip-tools 7.5.2** unter Python 3.12.15: direkte Vorgaben in `pyproject.toml` und
`requirements/*.in`, vollständige transitive Pins samt Hashes in
`requirements/build.txt`, `runtime.txt` und `dev.txt` pro Service. Das Hauptrepo
besitzt einen eigenen `requirements/dev.txt` für Vertrags- und Werkzeugprüfungen.
Die Aktualisierungsbefehle stehen in den Service-READMEs.

Simulator/Ingestion installieren den Dev-Lock als Wheels, dann das eigene Paket
mit `--no-deps --no-build-isolation`. Processing installiert zuerst den Build-Lock
als Wheels, dann den Dev-Lock mit `--no-build-isolation`, weil PyFlink Quellpakete
benötigt, und danach das eigene Paket. Java 17 und `JAVA_HOME` sind dort erforderlich;
Linux x86_64 ist geprüft, andere Plattformen nicht verifiziert. Der frühere
`processing/requirements-dev.lock` ist nur noch ein Verweis auf den neuen Lock;
`requirements/previous-versions.txt` bewahrt frühere Versionsconstraints.
Hashes fixieren Eingaben, garantieren keine bitweise identischen Docker-Layer.

Service-CI prüft Installation, `pip check`, pytest, Ruff und mypy für `src tests`
bei Push/PR; Docker-Build und Laufzeit-Smoke-Test nur nach Push auf `main`.
Hauptrepo-CI prüft Vertrag und Tools sowie separat Service-Kopien und Herkunft
mit vollständiger Historie. Workflow-Dateien definieren den tatsächlichen Umfang;
ein grüner Python-Lauf ersetzt keinen Container- oder Ende-zu-Ende-Nachweis.

Quellen:

- [pytest 9.1.1](https://pypi.org/project/pytest/9.1.1/)
- [Ruff 0.17.2](https://pypi.org/project/ruff/0.17.2/)
- [mypy 2.4.0](https://pypi.org/project/mypy/2.4.0/)

## 7. Implementierter Stand und ausstehende Nachweise

Der Repository-Abgleich vom 2. November 2026 umfasst die im Hauptrepo integrierten
Service-Stände aus SOLY-14 und deren README-, Lock-, Docker- und CI-Dateien.
Die README-Angaben vom 23. Oktober sind historische Nachweise aus der damaligen
Umgebung, keine im Rahmen von SOLY-17 erneut ausgeführten Builds:

| Bereich | Implementierung / dokumentierter Nachweis | Grenze |
|---|---|---|
| Simulator / Ingestion | Python-Basisimage per Digest, Hash-Locks, installierbares Paket und Container-Smoke-Test; Python-Version und Imports dokumentiert | keine Ereignisgenerierung, Adapter oder Broker-Verbindung |
| Processing | gemeinsames Rollenimage, Python-Quellbuild, PyFlink/Java, Connector-Lock, Klassenlade- und Table-Planungs-Smoke-Test | kein eingereichter fachlicher Job oder Datenbank-Schreibnachweis |
| Vertrag | zentrale v1-Spezifikation, Schemata/Beispiele, lokale Service-Kopien mit Commit und Hashes, Vertrags-/Herkunftsprüfungen | keine implementierte fachliche Pipeline |
| Kafka / PostgreSQL | Versionen ausgewählt, Client-/Connector-Artefakte gelockt | noch kein Gesamt-Compose, Broker-/DB-Start oder Ende-zu-Ende-Test |

Noch ausstehend sind insbesondere:

1. Kafka-/PostgreSQL-Basisimages beziehen, Digests erfassen und Gesamt-Setup bauen.
2. Bekannte Daten über JSONL/Ingestion → Kafka → PyFlink → PostgreSQL verarbeiten.
3. Erwartete Ergebnisse und idempotenten UPSERT tatsächlich prüfen.
4. Fachliche Event-Time-/Qualitätsfälle, Wiederherstellung nach Ausfällen,
   Realdatenvalidierung und Lasttests als eigene Nachweise ausführen.

Die v1-Semantik ist in [docs/data-contract.md](docs/data-contract.md) verbindlich;
veröffentlichte Artefakte und Service-Kopien samt Herkunftsmanifest sind
unveränderlich. Neue Semantik wird ausdrücklich versioniert. Tatsächliche lokale
und CI-Ergebnisse jeder Änderung gehören in den jeweiligen PR.

## 8. Änderungsregel und noch offene Detailentscheidungen

Versionsänderungen erfolgen bewusst und nachvollziehbar. Bei Änderungen an Flink oder PyFlink werden beide gemeinsam aktualisiert und die Connector-Versionen erneut geprüft. Nach Änderungen an Laufzeit- oder Connector-Abhängigkeiten werden die betroffenen Build-/Smoke-Tests erneut ausgeführt; sobald vorhanden, zusätzlich der vollständige Integrationstest. Sicherheits- und Fehlerkorrekturen werden geprüft und nicht allein wegen des ursprünglichen Versionspins ausgeschlossen.

Noch nicht durch dieses Dokument festgelegt sind insbesondere:

- Konkrete Docker-Engine- und Compose-Plugin-Version auf Entwicklungs- und CI-Rechnern.
- Kafka-/PostgreSQL-Image-Digests für das kommende Gesamt-Setup.
- Plattform-Lockstände außerhalb der bisher geprüften Umgebungen.
- Weitere Bibliotheken, etwa für Home-Assistant-WebSocket-Zugriff und Konfigurationsvalidierung.
- Die fachliche Sink-Implementierung auf Basis der bereits gewählten JDBC-Table-API und gelockten Abhängigkeiten.

Das Python-Lock-Verfahren, die Service-Basis-Digests, der historische Java-Patchstand und die JDBC-API/Abhängigkeitsauflösung sind inzwischen festgelegt (siehe oben). Die verbleibenden Punkte werden beim weiteren Infrastruktur- und Pipeline-Setup ergänzt. Sie ändern nicht die hier ausgewählten Kernversionen, solange sich bei der praktischen Prüfung kein begründeter Anpassungsbedarf ergibt.
