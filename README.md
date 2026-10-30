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
