# SOLY-18: Entwicklungsbefehle und Validierung

Die Entwicklungsbefehle sind **unter Linux und Windows getestet**. Hauptrepo,
Simulator und Ingestion verwenden unter beiden Betriebssystemen dieselben
Prüfschritte und Hash-Locks. Processing verwendet Linux x86_64 mit Java 17;
unter Windows wird dieser Linux-Weg über WSL2 oder Linux-Container ausgeführt.

## Prüfstand vom 19. November 2026

Grundlage sind die aktuellen `SOLY-18_development_commands`-Branches und die
unten beschriebenen Korrekturen in den Arbeitskopien:

| Repository | Abgerufener Commit |
|---|---|
| Hauptrepo | `a70f894840f6df68573d2a97f6ca527d657cda39` |
| Simulator | `cc744de51e7db037301e74c93fcc1bcd13c20718` |
| Ingestion | `afe09821d7e80b312bde4fd00350cca546072f90` |
| Processing | `a6cbe41b1fded93ba976cf540a3b0068158fdb85` |

Die Commit-IDs bezeichnen die Ausgangsstände vor den anschließend geprüften
lokalen Korrekturen.

| Umgebung | Python | Shells | Umfang |
|---|---|---|---|
| Windows 10 x86_64, Build 19045 | 3.12.10 | Windows PowerShell 5.1.19041.6456 und PowerShell 7.6.9 | Hauptrepo, Simulator, Ingestion; Processing-Plattformprüfung |
| Linux x86_64, Ubuntu 22.04.5 unter WSL2 | 3.12.16 | POSIX-Shell und PowerShell 7.5.4 | Hauptrepo, Simulator, Ingestion; Processing mit Java 17 |

WSL2 verwendet Kernel `6.18.58.1-microsoft-standard-WSL2`. Die Linux-PowerShell
wurde als temporäres Werkzeug anhand des offiziellen Release-Hashes geprüft.
Windows und Linux besitzen getrennte virtuelle Umgebungen. Lokal sind
3.12-Patchstände zugelassen; CI und Container behalten Python 3.12.15.

## Einrichtung und Prüfungen

Zusätzlich zum bestehenden Windows-Checkout wurden die Projekte als frische,
eigenständige Kopien ohne `.venv`, Git-Metadaten oder benachbarte Services geprüft.
Die Kopien liegen in Pfaden mit Leerzeichen. Alle Aufrufe erfolgen außerhalb des
jeweiligen Repository-Verzeichnisses.

Für Hauptrepo, Simulator und Ingestion bestanden unter beiden Betriebssystemen:

- frisches `setup`, wiederholtes `setup` mit Erhalt der bestehenden `.venv`;
- vollständiges `check` über beide Shell-Einstiege: Linux mit POSIX-Shell und
  PowerShell 7, Windows mit Windows PowerShell 5.1 und PowerShell 7;
- `setup/check --use-current-python` in der virtuellen Umgebung;
- `format` über beide Einstiege, ohne Änderung der bereits formatierten Dateien.

`check` umfasst `pip check`, pytest, Ruff-Linting, Ruff-Formatprüfung und mypy
einschließlich `scripts/`. Dateiinhalt und Änderungszeit der Projektdateien blieben
bei den Prüfungen unverändert. Die pytest-Ergebnisse pro Standardlauf:

| Repository | Linux | Windows |
|---|---|---|
| Hauptrepo | 113 bestanden | 106 bestanden, 7 übersprungen |
| Simulator | 33 bestanden | 26 bestanden, 7 übersprungen |
| Ingestion | 33 bestanden | 26 bestanden, 7 übersprungen |
| Processing | 33 bestanden | Linux-Weg; native Plattformabgrenzung geprüft |

Die sieben unter Windows übersprungenen Fälle betreffen den Unix-Einstieg und
ausführbare Unix-Testattrappen; sie werden unter Linux vollständig ausgeführt.
Die separaten Integrationsfälle sind im Standardlauf des Hauptrepos abgewählt.

Ingestion wurde unter Windows zusätzlich mit isoliertem Python importiert:
confluent-kafka 2.16.0 und die native librdkafka 2.16.0 wurden erfolgreich geladen.

Im vollständigen Hauptrepo mit Historie und allen drei Unterrepos bestanden
jeweils **19 Integrationsprüfungen** über `check-integration`: unter Linux über
POSIX-Shell und PowerShell 7, unter Windows über PowerShell 7 und Windows
PowerShell 5.1. Sie prüfen Vertragskopien, Hashes und Herkunft sowie gemeinsame
Entwicklungsskripte einschließlich der Prüfungen gegen abweichende Kopien.

## Processing und Container

Processing bestand denselben vollständigen Ablauf unter Linux in WSL2:
frisches und wiederholtes Setup, Checks und Formatierung über POSIX-Shell und
PowerShell 7 sowie Setup/Check mit dem aktuellen virtuellen Interpreter.
`JAVA_HOME` verwies auf **Temurin 17.0.20.1+1**, temporär aus dem unveränderten
Flink-Basisimage bereitgestellt, ohne globale Java-Installation.

Die native Plattformabgrenzung wurde unter Windows mit beiden PowerShell-Versionen
geprüft: `setup`, `check` und `format` enden jeweils mit Fehlercode 1 und einem
Linux-/WSL2-Hinweis, bevor eine `.venv` angelegt wird.

Aktuelle Container-Builds und isolierte Laufzeit-Smoke-Tests auf **linux/amd64**
mit Docker Engine **29.1.3**:

| Service | Aktueller Build und `docker-smoke` |
|---|---|
| Simulator | erfolgreich |
| Ingestion | erfolgreich |
| Processing | erfolgreich |

Die Smoke-Tests laufen mit `--network none`, ohne Mounts und außerhalb des
Quellbaums. Simulator und Ingestion verwenden `--read-only`; Processing behält
seine temporär beschreibbaren Verzeichnisse und den expliziten Python-Einstieg.
Geprüft werden Paketinstallation und Metadaten mit Python 3.12.15, bei Ingestion
zusätzlich der Kafka-Client und bei Processing PyFlink/Flink 2.2.1, Java 17 sowie
Connector-Klassen und Table-Pläne. Die Tabelle dokumentiert die aktuellen
Ergebnisse; frühere Nachweise sind unten gesondert datiert.

## Korrekturen aus dem Durchlauf

- `dev.sh` ist in allen vier Repositories wieder als ausführbare Datei versioniert.
  Ein frischer Linux-Checkout kann den dokumentierten Aufruf `./dev.sh` verwenden.
- Die drei Service-Paketmetadaten erlauben `>=3.12,<3.13`, passend zur bestehenden
  lokalen Versionsprüfung. Die Paketinstallation akzeptiert damit die lokal
  vorgesehenen 3.12-Patchstände.
- Der gemeinsame Regressionstest verwendet den eigenen `subprocess`-Import
  statt eines nicht exportierten Attributs aus `scripts.dev`; mypy besteht.
  Dieselbe Testdatei ist in allen vier Repositories nach Ruff formatiert.
- Die gemeinsame `.gitattributes` legt für XML-Dateien LF-Zeilenenden fest.
  Dadurch bleibt der Hash der Connector-Konfiguration unter Linux und Windows
  identisch. Der Git-Export wurde unter Windows geprüft; die vorhandene POM-
  Hashvorgabe und der Connector-Lock wurden unverändert beibehalten.

Veröffentlichte Vertragsartefakte, Herkunftsmanifeste, Hash-Locks, `.python-version`,
CI-Laufzeitpins und Image-Digests bleiben unverändert. Die Paket-Metadatenregel
ändert die lokal zugelassenen Interpreter, nicht die Abhängigkeitsversionen.

## CI, frühere Nachweise und Umfang

Die bestehende CI verwendet Ubuntu 24.04 und Python 3.12.15 mit den gemeinsamen
Einstiegen einschließlich PowerShell 7. Ein zusätzlicher Job prüft frisches und
wiederholtes lokales Setup in einem Checkout-Pfad mit Leerzeichen, den Erhalt
der `.venv` und anschließende Checks ohne `--use-current-python`. Docker-Jobs
laufen nach Push auf `main` und erfolgreichen Python-Prüfungen. Die lokalen
Windows-Ergebnisse sind ein eigener Nachweis, kein Windows-CI-Lauf.

Der frühere Nachweis vom **3. November 2026** verwendete Linux x86_64, Python
3.12.15 und PowerShell 7.5.4, für Processing zusätzlich OpenJDK 17. Damals
bestanden 95 Hauptrepo-Tests, je 15 Service-Tests und 9 Integrationsprüfungen.
Alle drei Container-Smoke-Tests wurden auf linux/amd64 erfolgreich ausgeführt.
Diese Zahlen gehören zum damaligen Testumfang und ersetzen keine aktuellen Läufe.

Der vorhandene Testumfang prüft Projektwerkzeuge, Verträge, Paketinstallation
und Laufzeit-Smoke-Tests. Ein fachlicher Durchlauf von Ingestion über Kafka und
Flink bis PostgreSQL ist noch nicht implementiert. Klassen- und Table-Planungsprüfungen
sind kein eingereichter Streaming-Job oder Datenbank-Schreibnachweis. macOS wurde
nicht geprüft.

## Abschlussintegration vom 19. November 2026

Die Service-PRs wurden nach erfolgreichen PR-Prüfungen gemergt. Das Hauptrepo
integriert die tatsächlich resultierenden, veröffentlichten `main`-Commits:

| Service | Gemergter Commit | Pull Request | Erfolgreiche PR-CI |
|---|---|---|---|
| Simulator | `91beb000430cc69d767afd2ed89c800fa800a95b` | [#5](https://github.com/vegedy/Soly-Simulator/pull/5) | [CI](https://github.com/vegedy/Soly-Simulator/actions/runs/44501921167) |
| Ingestion | `97f3feef7b354877a757e9d88a8bbe53815a9645` | [#5](https://github.com/vegedy/Soly-Ingestion/pull/5) | [CI](https://github.com/vegedy/Soly-Ingestion/actions/runs/44501936743) |
| Processing | `edfcd03a7292d621482d04d1339eb3dd4c748229` | [#5](https://github.com/vegedy/Soly-Processing/pull/5) | [CI](https://github.com/vegedy/Soly-Processing/actions/runs/44501952235) |

Die Inhalte der Merge-Commits stimmen exakt mit den lokal geprüften Service-
Ständen überein. Mit diesen endgültigen Service-Verweisen wurde
`check-integration` erneut ausgeführt: **jeweils 19 Prüfungen bestanden**, unter
Windows mit Windows PowerShell 5.1 und PowerShell 7 sowie unter Linux mit
POSIX-Shell und PowerShell 7. Vertragskopien, Herkunft und gemeinsame
Entwicklungsdateien sind damit auch nach den Service-Merges geprüft.
