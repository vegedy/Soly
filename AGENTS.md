# Arbeiten an Soly

- Lies [CONTRIBUTING.md](CONTRIBUTING.md), den
  [Git-Workflow](Soly-Issue-und-Git-Workflow.md) und die
  [Technologieentscheidungen](Soly-Technologieentscheidungen.md).
  Der Quellcode der Services liegt in eigenständigen Git-Submodulen unter
  `simulator/`, `ingestion/` und `processing/`; beachte dort die jeweilige AGENTS.md.
- Issues werden zentral in `vegedy/Soly` geführt. Von aktuellem `main` aus pro
  betroffenem Repository `SOLY-<Nummer>_<beschreibung>` anlegen; nie im detached
  HEAD arbeiten. Commits und PR-Titel beginnen mit `SOLY-<Nummer>` (Englisch).
- Service-PRs verwenden `Refs vegedy/Soly#<Nummer>`. Nach ihrem Merge die
  resultierenden Service-Commits im Hauptrepo integrieren und prüfen. Nur der
  abschließende Hauptrepo-PR verwendet `Closes #<Nummer>`.
  Review und Merge übernimmt der Nutzer; keine PRs selbst freigeben oder mergen.
- [docs/data-contract.md](docs/data-contract.md) ist verbindlich.
  Veröffentlichte `contracts/v1/` und Service-Kopien nicht ändern; für geänderte
  Semantik eine neue Vertragsversion vorsehen. Kopien und `contracts/provenance.json`
  gemeinsam aus einem veröffentlichten Hauptrepo-Commit übernehmen und prüfen.
- Laufzeiten, Hash-Locks und Image-Digests bewusst ändern, Gründe dokumentieren
  und betroffene Installationen/Builds erneut prüfen. Keine Secrets oder privaten
  Rohdaten einchecken. Zukunftspläne nicht als implementiertes Verhalten ausgeben.
- Einrichtung und Prüfungen über `./dev.sh setup`, `./dev.sh check` und
  `./dev.sh check-integration`; unter PowerShell dieselben Befehle über `dev.ps1`.
  Kein Aktivieren der `.venv` nötig. `format` schreibt ausdrücklich Änderungen.
  `check` prüft pip, pytest, Ruff und mypy für `tests scripts`; die Integration
  benötigt initialisierte Submodule und vollständige Hauptrepo-Historie.
  Service-Prüfungen im jeweiligen Service ausführen. CI verwendet dieselben
  Einstiege mit `--use-current-python`. Tatsächliche Ergebnisse dokumentieren.
