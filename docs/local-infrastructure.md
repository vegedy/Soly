# Lokaler Infrastruktur-Stack

SOLY-19 startet einen einzelnen Kafka-KRaft-Broker/Controller, PostgreSQL sowie
Flink JobManager und einen TaskManager im Session-Modus. Es laufen noch kein
Simulator, Ingestion-Service oder fachlicher Flink-Job. Es gibt kein fachliches
Ergebnismodell und keinen Nachweis für Hochverfügbarkeit oder Checkpoint-Recovery.

## Voraussetzungen

- Git-Checkout mit vollständiger Historie und initialisierten Submodulen.
- Python 3.12.x für die Entwicklungsbefehle; keine `.venv`, Java- oder lokale
  PyFlink-Installation für die Stack-Befehle nötig.
- Docker Engine für **Linux amd64** und ein aktuelles **Compose-Plugin**
  (`docker compose`, mindestens 2.24; auch aktuelle 5.x-Versionen).
- Unter Windows Docker Desktop mit Linux-Containern/WSL2-Backend oder Docker
  Engine und Compose innerhalb von WSL2. Bei ausschließlich in WSL installiertem
  Docker die Befehle in dieser Distribution ausführen. `dev.ps1` richtet keine
  automatische Verbindung zu einer WSL-Docker-Engine ein.
- Anfängliche Empfehlung: vier CPU-Kerne, 8 GiB verfügbarer RAM für Docker/WSL
  und 20 GiB freier Speicher für Images und Build-Cache. Auf einem Windows-Host
  sind insgesamt 16 GiB RAM sinnvoll. Dies sind Entwicklungsrichtwerte;
  [gemessene Umgebungen und Grenzen](infrastructure-validation.md) separat beachten.

Der erste Build benötigt Netzwerkzugriff und baut das vorhandene Processing-Image
einschließlich Python und PyFlink. Weitere Builds verwenden den Docker-Cache;
die Werkzeuge verändern keine Laufzeitpins und laden keine Abhängigkeiten neu auf.
Docker/Compose müssen vorher eingerichtet sein; die Befehle installieren keine
Systemwerkzeuge und ändern weder Proxy noch globale Einstellungen.

## Frischer Checkout und Start

Linux beziehungsweise WSL2 (Checkout bevorzugt im Linux-Dateisystem):

```bash
git clone --recurse-submodules git@github.com:vegedy/Soly.git
cd Soly
cp .env.example .env
./dev.sh stack-build
./dev.sh stack-up
./dev.sh stack-status
./dev.sh stack-smoke
```

Windows PowerShell mit erreichbarem Docker für Linux-Container:

```powershell
git clone --recurse-submodules git@github.com:vegedy/Soly.git
Set-Location Soly
Copy-Item .env.example .env
.\dev.ps1 stack-build
.\dev.ps1 stack-up
.\dev.ps1 stack-status
.\dev.ps1 stack-smoke
```

`stack-up` führt den gecachten Build ebenfalls aus. Der separate Build-Befehl
ist praktisch für die Einrichtung, aber vor `stack-up` nicht zwingend nötig.
Processing muss sauber sein und dem im Hauptrepo gespeicherten Commit entsprechen;
die Befehle aktualisieren keine Submodule. Bei fehlenden Submodulen zuerst
`git submodule update --init --recursive` ausführen.

Alle Stack-Befehle akzeptieren `--env-file PATH` und `--project-name NAME`.
Ohne `--env-file` wird die `.env` im Hauptrepo verwendet, auch bei einem Aufruf
aus einem anderen Verzeichnis. Ein ausdrücklich übergebener relativer Dateipfad
bezieht sich auf das aktuelle Verzeichnis. Beispiel ohne lokale Konfigurationskopie:

```bash
"/pfad mit Leerzeichen/Soly/dev.sh" stack-up \
  --env-file "/pfad mit Leerzeichen/Soly/.env.example" --project-name soly-demo
```

Unter PowerShell denselben Aufruf mit `& 'C:\Pfad mit Leerzeichen\Soly\dev.ps1'`
beginnen. Die geltende Ausführungsrichtlinie wird nicht verändert. Falls sie
Skripte sperrt, den Python-Einstieg verwenden: `py -3.12 scripts/dev.py stack-up`.

## Konfiguration und Adressen

`.env.example` enthält ausschließlich öffentliche lokale Beispielwerte; echte
Zugangsdaten gehören nur in die ignorierte `.env` oder in die Prozessumgebung.
Sie werden zur Laufzeit übergeben, niemals als Buildargumente oder Image-Dateien.
Compose verwendet seine übliche Priorität: Prozessumgebung vor Env-Datei vor
Compose-Standardwert. `--project-name` hat Vorrang vor `COMPOSE_PROJECT_NAME`.

| Einstellung | Standard / Bedeutung |
|---|---|
| `COMPOSE_PROJECT_NAME` | `soly`; trennt Container, Netzwerk und benannte Volumes |
| `SOLY_KAFKA_PORT` | `9092`; Host-Adresse `localhost:9092` |
| `SOLY_POSTGRES_PORT` | `5432`; intern `postgres:5432` |
| `SOLY_FLINK_PORT` | `8081`; Oberfläche und REST unter `http://localhost:8081` |
| `SOLY_KAFKA_TOPIC` | `soly-infra-smoke`; konfigurierbares Test-Topic |
| `SOLY_KAFKA_PARTITIONS` | `1`; Replikationsfaktor ist im Einzelbroker-Stack 1 |
| `SOLY_POSTGRES_DB` / `SOLY_POSTGRES_USER` | jeweils `soly` |
| `SOLY_POSTGRES_PASSWORD` | erforderlich; Beispiel `soly-local-example-only` |
| `SOLY_KAFKA_HEAP` | `-Xms512m -Xmx512m` |
| `SOLY_JOBMANAGER_MEMORY` | `1024m` Prozessspeicher |
| `SOLY_TASKMANAGER_MEMORY` | `2048m` Prozessspeicher |
| `SOLY_TASK_SLOTS` | `2` |
| `SOLY_STACK_TIMEOUT` | `180` Sekunden je Bereitschaftsphase |

Alle Host-Ports binden ausschließlich an **127.0.0.1**. Intern verwenden Kafka-
Clients **`kafka:19092`**, Host-Clients **`localhost:<SOLY_KAFKA_PORT>`**. Kafka
veröffentlicht diese getrennten Adressen in seinen Broker-Metadaten. Controller-
Port 9093 und Flink-RPC-Ports werden nicht auf dem Host veröffentlicht. Der Stack
verwendet lokal Kafka PLAINTEXT; er ist für den eigenen Rechner vorgesehen.

Für ein zweites Projekt müssen neben dem Projektnamen auch freie Host-Ports
gewählt werden. Keine festen Container-Namen oder externen gemeinsamen Volumes.
Ein entfernter Docker-Daemon wird vom Host-Port-Smoke-Test nicht unterstützt.

## Bereitschaft, Topics und Datenerhalt

`stack-up` wartet begrenzt auf Kafka-Metadaten, PostgreSQL-Bereitschaft und den
Flink-REST-Endpunkt. Der TaskManager hängt vom gesunden JobManager ab; danach
wird ausdrücklich genau eine TaskManager-Registrierung geprüft. Ein gestarteter
Prozess allein ist kein erfolgreicher Infrastruktur-Nachweis.

Der Hilfsdienst `kafka-init` läuft bei jedem `stack-up` erneut, nachdem Kafka
bereit ist. Er erstellt ein fehlendes Topic und prüft die gewünschte Anzahl an
Partitionen sowie Replikationsfaktor 1. Ein vorhandenes abweichendes Topic führt
zum Fehler. Es wird weder verändert noch gelöscht; ein neuer Topic-Name oder
ein ausdrücklich gewünschter Reset sind bewusste Entscheidungen. Automatische
Broker-Topic-Erstellung ist ausgeschaltet, auch interne Replikationswerte sind 1.

Die feste lokale KRaft-Cluster-ID ist keine Zugangsinformation. Kafka-Daten liegen
im benannten Volume unter `/var/lib/kafka/data`. PostgreSQL 18 verwendet das
Volume **`/var/lib/postgresql`** und darin `18/docker`; der frühere Mountpunkt
`/var/lib/postgresql/data` wird nicht benutzt.

```bash
./dev.sh stack-down
./dev.sh stack-up
```

`stack-down` entfernt Container und Projektnetzwerk und erhält die benannten
Datenvolumes. Ein Startfehler führt ebenfalls zu keiner automatischen
Datenlöschung. Bestehende PostgreSQL-Volumes behalten ihre initialisierten
Benutzer und Passwörter; eine Änderung der Env-Datei migriert diese nicht.

**Reset löscht die Daten dieses Projekts ausdrücklich:**

```bash
./dev.sh stack-reset --yes
# PowerShell: .\dev.ps1 stack-reset --yes
```

Der Reset löscht ausschließlich die zu diesem Compose-Projekt gehörenden
Container und Volumes. Er führt kein Docker-Prune aus und entfernt keine Images,
Build-Caches, fremden Projekte oder Dateien auf dem Host. Ohne `--yes` wird der
Befehl vor dem ersten Docker-Aufruf abgelehnt.

## Prüfungen und Diagnose

`stack-status` zeigt Container-/Health-Zustände, Topic-Beschreibung und registrierte
TaskManager; bei fehlender Bereitschaft liefert er einen Fehlercode.
`stack-smoke` prüft:

- Kafka-Publish/Consume in einem eindeutigen temporären Infrastruktur-Topic.
  Nur dieses selbst erstellte Topic wird danach gelöscht.
- Eine lesende Kafka-Metadatenanfrage vom Host einschließlich der tatsächlich
  beworbenen externen Broker-Adresse und Erreichbarkeit aller Host-Ports.
- PostgreSQL über eine authentifizierte TCP-Verbindung mit `SELECT 1`.
- Genau einen registrierten TaskManager, gleiche Image-IDs beider Flink-Rollen,
  Python 3.12.15, PyFlink 2.2.1, Interpreterkonfiguration und alle gelockten JAR-Hashes.
- Den unveränderten isolierten Processing-Smoke-Test für JVM-/Connector-Laden
  und Table-API-Planung; dabei wird kein fachlicher Job eingereicht.

Logs bei Startproblemen, mit derselben Env-Datei und demselben Projektnamen:

```bash
docker compose --env-file .env --project-name soly ps --all
docker compose --env-file .env --project-name soly logs --tail 100
```

Bei belegten Host-Ports passende freie Ports konfigurieren. Bei Timeout Health-
und Dienstlogs prüfen und Ressourcen beziehungsweise `SOLY_STACK_TIMEOUT`
anpassen. Bei Konfigurationsfehlern `docker compose --env-file .env config --quiet`
verwenden. Die vollständige gerenderte Konfiguration enthält das Passwort und
gehört nicht in öffentliche Logs oder PRs.

Die umfangreiche, **destruktive Abnahmeprüfung** verlangt ein bisher unbenutztes
Projekt mit Präfix `soly19-validation-` und räumt ausschließlich dieses auf:

```bash
python3.12 -m scripts.validate_stack --project-name soly19-validation-manual-001
```

Sie prüft wiederholte Starts/Initialisierung, Ablehnung abweichender Topics,
Datenerhalt für Kafka und eine isolierte SQL-Testtabelle über `down`/`up` sowie
den getrennten Reset. Die SQL-Probetabelle ist kein Anwendungs-Ergebnismodell.
In CI läuft derselbe Test bei PRs nach `main`, Pushes auf `main` und manuell über
den Workflow **Local infrastructure**. Protokolle werden sieben Tage als Artefakte
aufbewahrt. Normale `check`-Prüfungen benötigen weiterhin keine laufenden Dienste.

## Fixierte Images

Am 19. November 2026 wurden die Docker-Hub-Manifeste für die bestehenden
Versionsentscheidungen aufgelöst. Compose fixiert die jeweiligen **linux/amd64-
Manifest-Digests**, nicht nur veränderliche Tags:

| Image | linux/amd64-Manifest |
|---|---|
| `apache/kafka:4.2.2` | `sha256:daa39dc85acd37b148fad74d6b22b60fa5f7fa05048a5c8aa3b654140c63dd58` |
| `postgres:18.6-bookworm` | `sha256:02fb3245e038f33536cf13bc6c4e59f21d07b0cea3c1fe1c07c6e8aa8f083bcc` |

Die zugehörigen Multiarch-Index-Digests waren für Kafka
`sha256:1213eb3943d551e5ed1fca7a4e109001cee35770b66a02a0c37a8964efe09b69`
und für PostgreSQL
`sha256:f1ea2a1a4fb7b68d4836be1fdcb8a6466a89b072158bf9d97663600538c294c5`.
Nachvollziehbare Inspektion ohne Image-Layer-Download:

```bash
docker manifest inspect --verbose apache/kafka:4.2.2
docker manifest inspect --verbose postgres:18.6-bookworm
```

Processing wird einmal aus dem unveränderten gespeicherten Service-Stand gebaut.
`stack-up` übergibt die resultierende lokale `sha256:`-Image-ID an beide Rollen;
es gibt keinen Registry-Push. Diese ID ist inhaltsadressiert, aber kein
Registry-Manifest-Digest. Die bereits gepinnte Flink-Basis, Python-Quellhashes,
Systemsnapshot und Connector-Locks stehen im Processing-README. Zeitstempel
können bei frischen Builds zu anderen lokalen Image-IDs führen; es wird keine
bitweise Gleichheit unabhängiger Builds behauptet. Der Smoke-Test vergleicht die
tatsächlich gestarteten IDs und Artefakte.
