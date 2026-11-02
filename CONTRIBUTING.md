# Zu Soly beitragen

## Orientierung

Alle Aufgaben werden als Issues in [vegedy/Soly](https://github.com/vegedy/Soly/issues)
geführt, auch bei Änderungen an einzelnen Services. Das Hauptrepo enthält den
versionierten [Ereignisvertrag](docs/data-contract.md), Vertragsprüfungen und die
konkreten Service-Commit-Verweise. Die Services sind eigenständige Repositories:

| Pfad | Repository | Verantwortung (Zielbild) |
|---|---|---|
| `simulator/` | [Soly-Simulator](https://github.com/vegedy/Soly-Simulator) | synthetische Rohmessungen und Replay-Datensätze |
| `ingestion/` | [Soly-Ingestion](https://github.com/vegedy/Soly-Ingestion) | Live-/Replay-Aufnahme, Validierung, Anlagenzuordnung und Kafka-Publishing einschließlich Ticks |
| `processing/` | [Soly-Processing](https://github.com/vegedy/Soly-Processing) | Kafka-Verarbeitung, fachliche Normalisierung, Event-Time-Energieintegration und PostgreSQL-Ergebnisse |

Aktuell bestehen Python-Paketfundamente, Lockdateien, Container-Smoke-Tests, CI
und Vertragskopien. Die fachliche Pipeline ist noch nicht implementiert.
[Technologieentscheidungen](Soly-Technologieentscheidungen.md) trennen ausgewählte
Versionen, implementierten Stand und ausstehende Nachweise. Der
[Git-Workflow](Soly-Issue-und-Git-Workflow.md) beschreibt die Namens- und
Integrationsregeln ausführlich. Die jeweilige AGENTS.md fasst Arbeitsregeln zusammen.

## Vom Issue zum integrierten Stand

1. Das zentrale Issue lesen: Umfang, Voraussetzungen und Akzeptanzkriterien
   prüfen. Änderungen auf tatsächlich betroffene Repositories begrenzen.
2. Den gespeicherten Gesamtstand mit vollständiger Historie klonen:

   ```bash
   git clone --recurse-submodules git@github.com:vegedy/Soly.git
   cd Soly
   ```

   Bei vorhandenem Checkout zuerst eigene Änderungen sichern und den Hauptrepo-
   `main` aktualisieren (`git switch main`, `git pull --ff-only`). Dann
   `git submodule update --init --recursive` ausführen. Das setzt Submodule auf
   die gespeicherten Commits und kann sie in einen **detached HEAD** versetzen.
   `git submodule update --remote` ist dagegen eine bewusste Versionsaktualisierung.
3. Im Hauptrepo und jedem zu ändernden Service vom aktuellen `origin/main`
   einen Arbeitsbranch anlegen. Beispiel für Issue #17 (im jeweiligen Repository):

   ```bash
   git fetch origin
   git switch -c SOLY-17_repository_guidance origin/main
   git status --short --branch
   ```

   Vor Service-Änderungen immer den aktiven Branch prüfen; jeder Service besitzt
   eigene Git-Historie und Remotes. Bei einem eigenständigen Service-Checkout
   gelten dieselben Schritte; ein Hauptrepo ist für Service-Prüfungen unnötig.
4. Implementieren und passend prüfen. Commits und PR-Titel auf Englisch, z. B.
   `SOLY-17 Document repository guidance`. Nur geprüfte, vorgesehene Dateien
   committen und den Branch mit `git push -u origin SOLY-17_repository_guidance`
   veröffentlichen. Diff prüfen und tatsächliche Testergebnisse dokumentieren.
5. Pro betroffenem Service einen PR nach `main` öffnen. In dessen Beschreibung
   `Refs vegedy/Soly#17` verwenden, ohne Abschluss-Schlüsselwort. Review und Merge
   führt der Nutzer durch; Coding-Agenten geben PRs nicht selbst frei und mergen
   sie nicht. Es entsteht dadurch keine zusätzliche Branch-Protection-Regel.
6. Nach dem Service-Merge im Hauptrepo-Arbeitsbranch die tatsächlich gemergten
   Service-Commits übernehmen. Beispiel für einen geänderten Simulator:

   ```bash
   git -C simulator fetch origin
   git -C simulator switch --detach <gemergter-service-commit>
   git diff --submodule=log
   git add simulator
   git commit -m "SOLY-17 Integrate repository guidance"
   ```

   Nur saubere Service-Arbeitskopien umschalten; übrige geänderte Services ebenso
   integrieren. Ein detached HEAD ist für das Fixieren eines fertigen Commits in
   Ordnung, für neue Entwicklung zuerst wieder einen Arbeitsbranch anlegen.
   Alle referenzierten Commits müssen gepusht und erreichbar sein.
7. Den integrierten Stand einschließlich `service_copies` prüfen und den Hauptrepo-
   Branch pushen. Der abschließende Hauptrepo-PR nach `main` nennt Service-PRs,
   Tests und Einschränkungen und verwendet `Closes #17`, sobald er die Aufgabe
   vollständig abschließt. Erst sein Merge durch den Nutzer schließt das Issue
   automatisch (bei entsprechender GitHub-Einstellung).

Wird der Hauptrepo-PR schon vor den Service-Merges vorbereitet, bleibt er ein
**Entwurf** mit `Refs vegedy/Soly#17`. Vorläufige Verweise auf gepushte Service-
Branch-Commits ausdrücklich kennzeichnen. Nach den Service-Merges müssen die
resultierenden Commits übernommen und die Integration erneut geprüft werden;
bei Squash/Rebase unterscheiden sie sich von den vorläufigen Commits. Erst dann
zum abschließenden PR mit `Closes #17` machen. Das Issue bis dahin offen lassen.
Bei reinen Hauptrepo-Aufgaben entfallen Service-PRs und Submodule-Aktualisierungen.

## Einrichtung und Prüfungen

Alle Python-Projekte verwenden Python **3.12.15** und eine eigene `.venv`.
Keine globale Paketinstallation. Befehle stets im jeweiligen Repository ausführen.

Hauptrepo unter Linux/macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes --only-binary=:all: -r requirements/dev.txt
python -m pip check
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy tests
python -m pytest -m service_copies
```

Unter Windows die ersten beiden Befehle durch `py -3.12 -m venv .venv` und
`.\.venv\Scripts\Activate.ps1` ersetzen. In neuen Shells die Umgebung erneut
aktivieren. Die Standardtests brauchen keine Dienste oder Submodule;
`service_copies` benötigt alle drei Submodule und die vollständige Hauptrepo-
Historie (in CI `fetch-depth: 0`). Das Hauptrepo ist kein installierbares Paket.

| Service | Einrichtung, Prüfungen und Build |
|---|---|
| Simulator | [README](simulator/README.md): hashgesicherter Dev-Lock, dann eigenes Paket ohne Abhängigkeitsauflösung/Build-Isolation installieren |
| Ingestion | [README](ingestion/README.md): derselbe Installationsweg, zusätzlich Kafka-Client im Runtime-Lock |
| Processing | [README](processing/README.md): Java 17 und `JAVA_HOME`; zuerst Build-Lock als Wheels, dann Dev-Lock mit `--no-build-isolation`, anschließend eigenes Paket; Linux x86_64 geprüft, andere Plattformen nicht verifiziert |

In jedem Service laufen `python -m pip check`, `python -m pytest`,
`python -m ruff check .`, `python -m ruff format --check .` und
`python -m mypy src tests`. Nicht pauschal `--only-binary=:all:` auf den Processing-
Dev-Lock anwenden: einige PyFlink-Abhängigkeiten benötigen Quell-Builds.
Versionslisten, Lock-Generatoren und Docker-Befehle stehen in den Service-READMEs.

Die Hauptrepo-CI führt Vertrags-, Lint-/Typ- und Herkunftsprüfungen bei Pushes und
PRs nach `main` aus. Service-CI führt Python-Prüfungen bei jedem Push und PR nach
`main` aus; Docker-Build und Smoke-Test laufen dort nur bei Push auf `main` nach
erfolgreichen Python-Prüfungen. Ein grüner PR-Lauf belegt keinen Docker-Build und
keinen Ende-zu-Ende-Durchlauf. Bei Laufzeit-/Lock-/Connectoränderungen zusätzlich
betroffene Images und Smoke-Tests gemäß Service-README prüfen. Für reine
Dokumentationsänderungen sind keine erneuten Image-Builds erforderlich.

## Verträge und bewusste Aktualisierungen

[docs/data-contract.md](docs/data-contract.md) ist die maßgebliche Spezifikation.
Veröffentlichte `contracts/v1/`-Artefakte sind unveränderlich. Jeder Service enthält
identische lokale Kopien und ein `contracts/provenance.json` mit veröffentlichtem
Hauptrepo-Commit und SHA-256-Hashes; die Service-README verlinkt die Spezifikation
auf genau diesem Commit. Keine Runtime-Downloads oder Imports aus Nachbarrepos.
Neue Semantik braucht eine neue Vertragsversion. Bei einer Vertragsaktualisierung
alle Artefakte, Herkunftsmanifest und unveränderlichen Spezifikationslink gemeinsam
übernehmen und die zentralen Vertrags-/Herkunftsprüfungen ausführen.

Direkte Abhängigkeiten, transitive Hash-Locks, Basis-Digests und Connector-Locks
nicht beiläufig erneuern. Grund, geänderte Eingaben und Validierung im PR nennen;
die Verfahren stehen in den Service-READMEs und im
[Technologiedokument](Soly-Technologieentscheidungen.md). Flink und PyFlink gemeinsam
bewerten, kompatible Connectoren beibehalten. Secrets, private Rohdaten, `.venv`,
Caches und generierte Artefakte gehören nicht in Commits. Fehlende oder gescheiterte
Prüfungen ausdrücklich nennen; historische Nachweise nicht als neue Tests ausgeben.
