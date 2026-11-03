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

Vertragsprüfungen benötigen nur Python **3.12.15**, keine Submodule und keine
laufenden Dienste. Einrichtung und alle Prüfkommandos stehen in der Spezifikation.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes --only-binary=:all: -r requirements/dev.txt
python -m pytest
```

Der separate Abgleich aller Service-Kopien benötigt initialisierte Submodule und
die vollständige Hauptrepo-Historie:

```bash
python -m pytest -m service_copies
```

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
