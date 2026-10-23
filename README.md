# Soly
Eine datenintensive Echtzeit-Datenpipeline zur Analyse einer Photovoltaik-Anlage mit Batteriespeichern im privaten Haushalt entwickelt. Untersuchte Fragestellungen: Welche Anteile tragen PV-Anlage, Batterien und Stromnetz zur Haushaltsversorgung bei und in wiefern werden Batterien vom Stromnetz geladen?

## Submodules

Die drei Komponenten `simulator`, `ingestion` und `processing` werden als Git-Submodules eingebunden.

Submodules initialisieren und auf die im Repository gespeicherten Commits aktualisieren:

```bash
git submodule update --init --recursive
```

Auf den neuesten Stand der jeweiligen `main`-Branches aktualisieren:

```bash
git submodule update --remote --recursive
```
