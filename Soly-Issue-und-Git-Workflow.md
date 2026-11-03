# Soly: Regeln für Issues und Git-Workflow

- **Entscheidungsdatum:** 23. Oktober 2026
- **Repository-Abgleich:** 2. November 2026 (SOLY-17)
- **Zweck:** Grundlage zum Formulieren zukünftiger GitHub-Issues und der zugehörigen Branches, Commits und Pull Requests.
- **Geltungsbereich:** Hauptrepository `soly` und die Service-Repositories `soly-simulator`, `soly-ingestion` und `soly-processing`.

## 1. Aufgaben zentral erfassen

Alle Issues werden zunächst zentral im Hauptrepository **`soly`** geführt. Auch Aufgaben, die ausschließlich einen Service betreffen, werden dort erfasst. Ein Issue kann Änderungen in mehreren Repositories umfassen.

Als Labels eignen sich `simulator`, `ingestion`, `processing`, `infrastructure` und `documentation`. Mehrere Labels können betroffene Komponenten gemeinsam kennzeichnen. Diese Namen sind Beispiele; die tatsächliche Label-Liste kann bei Bedarf erweitert werden.

GitHub Projects wird vorerst nicht benötigt. Ein Kanban-Board kann später als zusätzliche Ansicht auf die bestehenden Issues und Pull Requests ergänzt werden. Ein Milestone `Phase 2` ist ebenfalls optional.

## 2. Aufgabenkennung und Benennung

Die Kennung folgt der aus dem beruflichen Jira-Workflow übernommenen Form:

```text
SOLY-<GitHub-Issue-Nummer>
```

Beispiel: Das Issue `#12` im Repository `soly` erhält die Kennung **`SOLY-12`**. Maßgeblich ist die tatsächlich von GitHub vergebene Nummer; Nummern werden nicht vorab als vergeben angenommen.

`SOLY-12` ist eine eigene Namenskonvention. Für GitHub-Verknüpfungen wird zusätzlich `#12` beziehungsweise repositoryübergreifend `vegedy/Soly#12` verwendet. Die tatsächlichen Repository-Namen sind `vegedy/Soly`, `vegedy/Soly-Simulator`, `vegedy/Soly-Ingestion` und `vegedy/Soly-Processing`.

| Element | Konvention | Beispiel |
|---|---|---|
| Issue-Titel | `SOLY-<Nummer> <Aufgabe>` | `SOLY-12 Implement JSONL replay adapter` |
| Branch | `SOLY-<Nummer>_<kurze_beschreibung>` | `SOLY-12_jsonl_replay` |
| Commitmessage | `SOLY-<Nummer> <Änderung>` | `SOLY-12 Add JSONL replay adapter` |
| Pull-Request-Titel | `SOLY-<Nummer> <Ergebnis>` | `SOLY-12 Implement JSONL replay adapter` |

Branches verwenden nach der Kennung eine kurze Beschreibung in Kleinbuchstaben mit Unterstrichen. Titel und Commitmessages werden entsprechend den bisherigen Beispielen auf Englisch formuliert; Issue- und PR-Beschreibungen können auf Deutsch verfasst werden.

Da GitHub die Issue-Nummer erst beim Erstellen vergibt, kann das Issue zunächst ohne Kennung angelegt und sein Titel anschließend ergänzt werden. In Entwürfen wird `SOLY-<Nummer>` verwendet.

## 3. Inhalt eines Issues

Ein Issue beschreibt eine klar abgegrenzte Aufgabe mit überprüfbarem Ergebnis. Es enthält:

1. **Beschreibung:** Was soll erreicht werden und warum?
2. **Umfang:** Welche konkreten Änderungen gehören zur Aufgabe?
3. **Akzeptanzkriterien:** Woran lässt sich die erfolgreiche Umsetzung erkennen?

Betroffene Repositories, Abhängigkeiten zu anderen Issues und bewusste Abgrenzungen werden ergänzt, wenn sie für die Aufgabe relevant sind. Die Akzeptanzkriterien beschreiben Ergebnisse und geeignete Nachweise. Noch nicht ausgeführte Prüfungen werden nicht als erfolgreich dargestellt.

### Vorlage

```markdown
# SOLY-<Nummer> <Task title>

## Beschreibung

<Ziel und Motivation der Aufgabe.>

## Umfang

- <Konkrete Änderung und gegebenenfalls betroffenes Repository.>

## Akzeptanzkriterien

- [ ] <Überprüfbares Ergebnis.>
- [ ] <Geeignete Validierung.>
```

Die erste Zeile dient als Issue-Titel; der übrige Text bildet die Beschreibung.

## 4. Branches und Entwicklung

Für jedes Issue wird in jedem betroffenen Repository ein eigener Arbeitsbranch auf Basis von `main` angelegt. Dieselbe Issue-Kennung wird über alle beteiligten Repositories hinweg verwendet. Beispielsweise kann `SOLY-12_jsonl_replay` sowohl in `soly-ingestion` als auch in `soly` existieren.

Es werden nur dort Branches und PRs angelegt, wo Änderungen anfallen. Ein reines Einbinden vorhandener Service-Repositories benötigt beispielsweise ausschließlich einen Branch im Hauptrepo.

Die Service-Entwicklung kann direkt in den Submodule-Arbeitskopien erfolgen:

```text
soly/
├── simulator/     # Repository soly-simulator
├── ingestion/     # Repository soly-ingestion
└── processing/    # Repository soly-processing
```

Zusätzliche Klone neben dem Hauptrepo sind nicht erforderlich. Jedes Submodule besitzt eigene Branches, Commits und Remotes. Vor Änderungen ist sicherzustellen, dass ein Arbeitsbranch aktiv ist: Submodule können nach dem Klonen oder Aktualisieren auf einem Commit ohne aktiven Branch stehen (detached HEAD).

## 5. Pull Requests und Abschluss einer Aufgabe

Der vereinbarte Ablauf ist:

1. Issue mit Ziel, Umfang und Akzeptanzkriterien erstellen.
2. Arbeitsbranch in jedem betroffenen Repository anlegen.
3. Änderungen implementieren und passend zur Aufgabe prüfen.
4. Pro betroffenem Repository einen Pull Request nach `main` öffnen.
5. Diff prüfen, verfügbare CI-Ergebnisse kontrollieren und tatsächliche Validierung dokumentieren. Review und Merge übernimmt der Nutzer; Coding-Agenten geben keine PRs selbst frei und mergen sie nicht.
6. Service-PRs mergen und die resultierenden Commit-Stände im Hauptrepo übernehmen.
7. Den abschließenden Hauptrepo-PR prüfen und mergen.
8. Issue schließen, sobald die Akzeptanzkriterien erfüllt sind und die Aufgabe im Gesamtsystem funktioniert.

Bei einer Aufgabe, die nur das Hauptrepo betrifft, entfallen die Service-PRs. Die inhaltliche Diff-Prüfung durch den Autor ersetzt nicht das vom Nutzer gewünschte persönliche Review. Es wird kein zusätzlicher Freigabeprozess und keine Branch-Protection-Regel eingerichtet.

### Verknüpfung mit dem zentralen Issue

Service-PRs referenzieren das Issue ohne vorzeitigen Abschluss:

```text
Refs vegedy/Soly#12
```

Erst der abschließende PR im Hauptrepo verwendet:

```text
Closes #12
```

So bleibt ein Issue bei Änderungen über mehrere Repositories hinweg offen, bis die Integration abgeschlossen ist. Die automatische Schließung setzt die entsprechende GitHub-Einstellung und einen Merge in den Standardbranch voraus; für Soly wird `main` als Standardbranch verwendet.

### PR-Beschreibung

Die Beschreibung erläutert das konkrete Ergebnis und nennt die tatsächlich durchgeführten Prüfungen. Offene oder fehlgeschlagene Prüfungen werden entsprechend gekennzeichnet. Ein Abschlussverweis wird nur gesetzt, wenn der PR die Aufgabe abschließt.

## 6. Besonderheiten der Submodule

Das Hauptrepo speichert pro Submodule einen konkreten Commit-Verweis. Neue Commits in einem Service werden nicht automatisch in den Stand des Hauptrepos übernommen.

Es gilt folgende Reihenfolge:

1. Änderungen im Service-Repository committen, pushen und dessen PR mergen.
2. Im Submodule den gemergten Service-Commit auschecken.
3. Den neuen Commit-Verweis auf dem Arbeitsbranch des Hauptrepos committen und pushen.
4. Den Hauptrepo-PR einschließlich der integrierten Service-Stände prüfen und mergen.

Der Hauptrepo-Stand muss auf erreichbare, gepushte Service-Commits verweisen. Das gilt insbesondere für Abgabestände. Branch- und Commitmessages im Hauptrepo verwenden dieselbe zentrale Issue-Kennung.

Ein vor den Service-Merges vorbereiteter Hauptrepo-PR bleibt ein Entwurf mit
`Refs vegedy/Soly#<Nummer>`. Vorläufige Verweise dürfen nur auf erreichbare,
gepushte Service-Commits zeigen und müssen als vorläufig gekennzeichnet sein.
Nach dem Merge durch den Nutzer die tatsächlich resultierenden Service-Commits
übernehmen (insbesondere bei Squash/Rebase), die Integration erneut prüfen und erst
dann `Closes #<Nummer>` setzen. Ein Entwurf schließt das Issue nicht vorzeitig.
Konkrete Befehle und Prüfungen stehen in [CONTRIBUTING.md](CONTRIBUTING.md).

## 7. Beispiel: Submodule erstmals integrieren

Das folgende Beispiel nimmt an, dass GitHub der Aufgabe tatsächlich die Nummer **#1** zugeteilt hat. Es ist ein Muster und kein Nachweis eines bereits angelegten Issues oder ausgeführter Prüfungen.

- **Repository des Issues:** `soly`
- **Issue-Titel:** `SOLY-1 Integrate service repositories as Git submodules`
- **Branch im Hauptrepo:** `SOLY-1_integrate_submodules`
- **Commitmessage:** `SOLY-1 Add service repositories as submodules`
- **Optionale separate Dokumentations-Commitmessage:** `SOLY-1 Document cloning and initializing submodules`
- **PR-Titel:** `SOLY-1 Integrate service repositories as Git submodules`
- **Abschlussverweis im Hauptrepo-PR:** `Closes #1`
- **Service-Branches und Service-PRs:** Nicht erforderlich, solange dort keine Inhalte geändert werden.

### Issue-Beschreibung

Die Repositories `soly-simulator`, `soly-ingestion` und `soly-processing` sollen als Git-Submodule in das Hauptrepository `soly` eingebunden werden. Dadurch erhält das Gesamtsystem einen zentralen Einstiegspunkt und einen reproduzierbaren Versionsstand aller Komponenten.

**Umfang**

- `soly-simulator` unter `simulator/` einbinden.
- `soly-ingestion` unter `ingestion/` einbinden.
- `soly-processing` unter `processing/` einbinden.
- In der README das vollständige Klonen und die Initialisierung der Submodule dokumentieren.

**Voraussetzung:** Alle drei Service-Repositories besitzen mindestens einen gepushten Commit, beispielsweise eine README.

**Akzeptanzkriterien**

- [ ] Alle drei Submodule sind in `.gitmodules` mit korrekten Repository-URLs und Pfaden eingetragen.
- [ ] Das Hauptrepository verweist auf erreichbare, gepushte Commits aller drei Unterrepos.
- [ ] Ein frischer Clone mit `git clone --recurse-submodules <repository-url>` enthält alle drei Unterrepos.
- [ ] Die README erklärt auch die nachträgliche Initialisierung mit `git submodule update --init --recursive`.
- [ ] Die dokumentierten Schritte wurden erfolgreich ausprobiert.

## 8. Implementierter Stand und Prüfungen

Die drei Service-Repositories sind bereits unter `simulator/`, `ingestion/` und
`processing/` eingebunden; Abschnitt 7 ist ein historisches Vorgehensbeispiel.
Der Ereignisvertrag v1 und seine Prüfungen sind in
[docs/data-contract.md](docs/data-contract.md) beschrieben. Die Services enthalten
identische Kopien unter `contracts/v1/` mit Herkunftsmanifesten, die in der
Hauptrepo-CI gegen einen veröffentlichten Commit geprüft werden. Veröffentlichte
v1-Artefakte sind unveränderlich; geänderte Semantik benötigt eine neue Version.

Einrichtung und Prüfkommandos stehen in [CONTRIBUTING.md](CONTRIBUTING.md) und
in den Service-READMEs. Das Hauptrepo hat Vertrags- und Herkunfts-CI; Services
haben Python-CI bei Push/PR und Docker-Smoke-Tests nur bei Push auf `main`.
Die fachliche Ende-zu-Ende-Pipeline ist noch kein nachgewiesener Bestandteil.
Nur tatsächlich ausgeführte lokale/CI-Prüfungen als erfolgreich dokumentieren.

## 9. Ergänzende Grundlagen

- [Technologie- und Versionsentscheidungen für Soly](Soly-Technologieentscheidungen.md)
- [Git: Submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- [GitHub: Pull Requests mit Issues verknüpfen](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)
- [GitHub: Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects)

Dieses Dokument legt keine zusätzliche Merge-Strategie, Branch-Protection-Regeln oder automatischen CI-Workflows fest. Solche Detailentscheidungen werden bei Bedarf ergänzt.
