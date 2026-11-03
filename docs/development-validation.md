# SOLY-18: Entwicklungsbefehle und Validierung

Nachweis vom **3. November 2026**. Gemeinsame Einstiege: `dev.sh`, `dev.ps1`
und die repository-lokale Standardbibliothek-Steuerung `scripts/dev.py`.
Die Services benötigen weder einen Hauptrepo-Checkout noch benachbarte Services.

## Tatsächlich lokal ausgeführt

Umgebung: **Linux x86_64**, **Python 3.12.15**, POSIX-Shell und
**PowerShell 7.5.4**; Processing zusätzlich mit **OpenJDK 17** und `JAVA_HOME`.
Die portable PowerShell wurde separat mit dem offiziellen Archiv-Hash geprüft;
sie ist keine Projektabhängigkeit und wird nicht eingecheckt.

Alle vier Repositories wurden zusätzlich als frische, eigenständige Kopien
ohne `.venv`, Git-Metadaten oder benachbarte Services in einem Pfad mit
Leerzeichen unter `/tmp` geprüft. Die Befehle wurden von außerhalb des jeweiligen
Repository-Verzeichnisses aufgerufen:

| Prüfung | Hauptrepo | Simulator | Ingestion | Processing |
|---|---|---|---|---|
| `setup` über Unix, danach erneut über PowerShell | erfolgreich | erfolgreich | erfolgreich | erfolgreich |
| `check` über Unix und PowerShell | erfolgreich | erfolgreich | erfolgreich | erfolgreich |
| `format` über Unix und PowerShell | erfolgreich | erfolgreich | erfolgreich | erfolgreich |
| `setup/check --use-current-python` im eingerichteten Interpreter | erfolgreich | erfolgreich | erfolgreich | erfolgreich |
| Projektdatei-Inhalte und Änderungszeiten vor/nach beiden Checks identisch | bestätigt | bestätigt | bestätigt | bestätigt |
| pytest im Standardlauf | 95 bestanden | 15 bestanden | 15 bestanden | 15 bestanden |
| pip check, Ruff-Linting, Ruff-Formatprüfung, mypy | erfolgreich | erfolgreich | erfolgreich | erfolgreich |

`format` ließ die bereits formatierten frischen Checkouts unverändert. Die
14 neuen Regressionstests je Repository prüfen unter anderem Versionsfehler,
Schutz vor globaler Installation, Erhalt unvollständiger Umgebungen, Hash-Locks
und Processing-Buildreihenfolge, nicht schreibende Prüfabläufe, fehlendes Java/
Docker, Plattformhinweise, Docker-Isolation sowie Argumente und Fehlercodes beider
Wrapper in Pfaden mit Leerzeichen.

Im vollständigen Hauptrepo-Checkout wurden außerdem `check-integration` über
Unix und PowerShell ausgeführt: **9 Prüfungen bestanden**, einschließlich
Vertragskopien, Hashes und Herkunft aus der veröffentlichten Hauptrepo-Historie.
Keine Lockdateien, Vertragsartefakte, Laufzeitpins oder Image-Digests wurden verändert.

## Container

`./dev.sh docker-smoke` lief in allen drei Services auf **linux/amd64** erfolgreich:

- Simulator: Python 3.12.15, installiertes Paket aus `site-packages` und Metadaten.
- Ingestion: dieselben Prüfungen sowie confluent-kafka 2.16.0 und librdkafka-Import.
- Processing: Python 3.12.15, PyFlink/Flink 2.2.1, Temurin 17.0.20.1,
  lokale Stream-/Table-Umgebung, vorhandene Kafka-/JDBC-/PostgreSQL-Klassen und
  Table-Pläne. Kein fachlicher Job oder Datenbank-Schreibnachweis.

Die bestehenden Smoke-Dateien und Container-Isolationsoptionen bleiben erhalten.
Die Wrapper bauen mit `--platform linux/amd64`; der anschließende Test läuft
mit `--network none`, ohne Mounts und außerhalb des Quellbaums. Simulator/Ingestion
verwenden weiter `--read-only`; Processing behält seine temporär beschreibbaren
Verzeichnisse und den expliziten Python-Einstieg.

## Plattformen und CI

Die CI nutzt dieselben Einstiege mit `--use-current-python` und erzeugt keine
zusätzliche `.venv`. Hauptrepo, Simulator und Ingestion besitzen Ubuntu-24.04-
und Windows-2025-Jobs, mit Checkout-Pfaden mit Leerzeichen und den jeweiligen
Unix-/PowerShell-Einstiegen. Processing bleibt auf Ubuntu 24.04 mit Java 17.
Docker-Jobs laufen weiterhin nur nach Push auf `main` und erfolgreichen Checks.

Die lokale Ausführung von PowerShell 7 unter Linux belegt weder natives Windows
noch Windows PowerShell 5.1 oder macOS. Für native Windows-Prüfungen gelten die
Actions-Ergebnisse des jeweils gepushten Commits. Windows PowerShell 5.1 und
macOS wurden lokal nicht ausgeführt. Processing lehnt native Windows-/macOS-
Entwicklung ab; unter Windows ist WSL2 mit Linux-Checkout oder der vorhandene
Linux-Container der beschriebene Weg. WSL2 selbst wurde lokal nicht ausgeführt.
Keine Skripte umgehen PowerShell-Richtlinien oder ändern globale Konfiguration.

## Vorläufige Integration ohne Pull Requests

Der Hauptrepo-Branch `SOLY-18_development_commands` verweist vorläufig auf die
gepushten Arbeitsbranch-Commits der drei Services. Es wurden keine Pull Requests
erstellt oder Merges ausgeführt; das Issue bleibt offen. Nach späteren Service-
Merges die tatsächlich resultierenden Commits im Hauptrepo übernehmen und
`check-integration` erneut ausführen, insbesondere bei Squash oder Rebase.
