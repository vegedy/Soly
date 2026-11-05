# Soly

Eine datenintensive Echtzeit-Datenpipeline zur Analyse einer Photovoltaik-Anlage
mit Batteriespeichern im privaten Haushalt. Untersucht werden die Beiträge von
PV-Anlage, Batterien und Stromnetz zur Haushaltsversorgung sowie die Netzladung
von Batterien.

## Ereignisvertrag v1

Die verbindliche Schnittstelle für Simulator/Replay → Ingestion → Kafka →
Processing steht in [docs/data-contract.md](docs/data-contract.md).
[contracts/v1/](contracts/v1/) enthält die versionierten JSON-Schemata, den
Sensorkatalog und ausschließlich synthetische Positiv-/Negativbeispiele.
Die Service-Implementierungen folgen in eigenen Issues.

## Entwicklungsbefehle

Voraussetzung: **Python 3.12.15**. `dev.sh` (POSIX-Shell unter Unix) und `dev.ps1`
(Windows PowerShell 5.1 oder PowerShell 7) delegieren an `scripts/dev.py` mit
Python-Standardbibliothek. Jeder Checkout besitzt eine eigene `.venv`; Aktivierung
ist unnötig. Die Befehle bestimmen den Repository-Pfad selbst. Auch ein Aufruf aus
einem anderen Verzeichnis oder ein Checkout-Pfad mit Leerzeichen funktioniert:

```bash
"/pfad mit Leerzeichen/Soly/dev.sh" setup
"/pfad mit Leerzeichen/Soly/dev.sh" check
```

Im Repository unter Unix:

```bash
./dev.sh setup
./dev.sh check
./dev.sh format
```

Unter Windows PowerShell (mit vorhandenem Python 3.12.15):

```powershell
.\dev.ps1 setup
.\dev.ps1 check
.\dev.ps1 format
# Aus einem anderen Verzeichnis:
& 'C:\Projekte mit Leerzeichen\Soly\dev.ps1' check
```

| Befehl | Wirkung |
|---|---|
| `setup` | Erstellt oder verwendet `.venv`, installiert vorhandene Hash-Locks und prüft Abhängigkeiten. Erneut ausführbar; keine Lock-Neuauflösung. |
| `check` | `pip check`, pytest, Ruff-Linting, Ruff-Formatprüfung und mypy einschließlich `scripts/`; stoppt beim ersten Fehler. |
| `format` | Schreibt ausdrücklich Ruff-Formatänderungen in Projektdateien. |
| `check-integration` | Prüft Service-Vertragskopien und Herkunft; benötigt initialisierte Submodule und vollständige Hauptrepo-Historie. |

`check` formatiert keine Dateien und legt Tool-Caches/Bytecode nicht im Checkout
an. Externe Fehlercodes werden weitergegeben. Kein Befehl aktualisiert Submodule,
löscht lokale Daten oder verändert globale Systemeinstellungen.

Interpreterwahl: `SOLY_PYTHON` (ein vollständiger Dateipfad, keine zusätzlichen
Argumente), vorhandene `.venv`, dann `python3.12`/`python3`/`python` unter Unix;
PowerShell versucht vor den Python-Befehlen zusätzlich `py -3.12`. Eine ungeeignete
Python-Version oder unvollständige `.venv` führt zu einem Hinweis, nicht zum
Löschen/Ersetzen. Bei Bedarf die vorhandene Umgebung zuerst selbst prüfen und
beiseitelegen. Einen bestimmten Interpreter auswählen:

```bash
SOLY_PYTHON='/pfad zu Python/bin/python3.12' ./dev.sh setup
```

```powershell
$env:SOLY_PYTHON = 'C:\Pfad zu Python\python.exe'
.\dev.ps1 setup
```


**Windows-Weg:** Mit den bestehenden Pins zunächst **WSL2** und die Unix-Befehle
in einem Linux-Checkout verwenden. `actions/setup-python` konnte Python 3.12.15
auf Windows 2025 nicht bereitstellen. Der native PowerShell-Einstieg setzt einen
selbst bereitgestellten Python-3.12.15-Interpreter voraus (`SOLY_PYTHON`); dieser
native Installationsweg und Windows PowerShell 5.1 sind bislang nicht verifiziert.
Es wird nicht automatisch auf eine andere Python-Version ausgewichen.

Falls die lokale PowerShell-Richtlinie Skripte sperrt, die geltende Richtlinie
prüfen oder den Python-Einstieg direkt aufrufen; die Skripte ändern keine
Sicherheitseinstellungen und verwenden keinen Execution-Policy-Bypass:

```powershell
py -3.12 scripts/dev.py setup
& .\.venv\Scripts\python.exe scripts/dev.py check
```

Die CI nutzt `setup --use-current-python` und `check --use-current-python` mit dem
bereits durch Actions eingerichteten Python. Lokal erlaubt `setup` diese Option
nur in einer virtuellen Umgebung; außerhalb davon ist sie ausschließlich mit
`CI=true` vorgesehen. Normalerweise ohne diese Option arbeiten. Die Skripte und
Textdateien verwenden festgelegte Zeilenenden; Vertragsartefakte behalten über
`.gitattributes` ihre exakten Bytes.

Das Hauptrepo installiert ausschließlich `requirements/dev.txt` als gehashte
Wheels und kein eigenes Paket. Die Standardprüfungen benötigen weder Submodule
noch laufende Dienste. Der separate Abgleich benötigt den gespeicherten
Gesamtstand und die vollständige Hauptrepo-Historie:

```bash
./dev.sh check-integration
# PowerShell: .\dev.ps1 check-integration
```

Ruff im Hauptrepo schließt die eigenständigen Service-Verzeichnisse aus;
Service-Prüfungen werden im jeweiligen Service separat ausgeführt.
Die CI prüft das Hauptrepo unter Ubuntu 24.04 über Unix und PowerShell 7,
jeweils in einem Checkout-Pfad mit Leerzeichen. Der separate
Integrationsjob läuft unter Ubuntu mit vollständiger Historie und Submodulen.
Tatsächlich ausgeführte lokale Tests und Plattformgrenzen: [Validierung](docs/development-validation.md).

## Submodules

Die Komponenten `simulator`, `ingestion` und `processing` sind eigenständige
Git-Repositories. Den gespeicherten Gesamtstand klonen:

```bash
git clone --recurse-submodules git@github.com:vegedy/Soly.git
```

Vorhandene Submodule auf die im Hauptrepository gespeicherten Commits bringen:

```bash
git submodule update --init --recursive
```

Ein bewusstes Aktualisieren auf die jeweiligen neuesten `main`-Stände verändert
dagegen den gespeicherten Gesamtstand und muss anschließend geprüft werden:

```bash
git submodule update --remote --recursive
```

## Mitarbeit und Projektentscheidungen

- [CONTRIBUTING.md](CONTRIBUTING.md): Repository-Aufbau, Einrichtung, Prüfungen und
  vollständiger Weg vom zentralen Issue bis zum integrierten Service-Stand.
- [AGENTS.md](AGENTS.md): kurze Arbeitsregeln für Coding-Agenten.
- [Soly-Issue-und-Git-Workflow.md](Soly-Issue-und-Git-Workflow.md): SOLY-Namenskonventionen,
  Service-PRs und Submodule-Integration; Review und Merge übernimmt der Nutzer.
- [Soly-Technologieentscheidungen.md](Soly-Technologieentscheidungen.md): ursprüngliche
  Versionswahl, inzwischen implementierte Locks/Container/CI und ausstehende Nachweise.

Service-spezifische Einrichtung und Prüfungen stehen in den READMEs unter
[simulator/](simulator/README.md), [ingestion/](ingestion/README.md) und
[processing/](processing/README.md). Insbesondere Processing benötigt einen eigenen
Installationsweg für PyFlink-Quellabhängigkeiten und Java 17.

Die CI prüft zusätzlich den lokalen Setup-Weg in einem frischen Checkout mit
Leerzeichen: Unix-Setup, erneutes PowerShell-Setup mit Erhalt der bestehenden
`.venv`, danach `check` über beide Einstiege ohne `--use-current-python`.
Alle Aufrufe dieses Jobs erfolgen außerhalb des Checkout-Verzeichnisses.
