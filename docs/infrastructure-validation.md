# SOLY-19: Infrastruktur-Prüfprotokoll

Stand: 19. November 2026. Die Implementierung und die fixierten Digests stehen
in der [Stack-Anleitung](local-infrastructure.md).

## Umgebung und Werkzeugprüfungen

- Windows, Python 3.12.10: Hauptrepo-Prüfungen einschließlich pip, pytest,
  Ruff und mypy erfolgreich; 121 Tests bestanden, acht plattformabhängig übersprungen.
- Vertrags-/Herkunfts-/Werkzeugabgleich: 20 Tests erfolgreich.
- Compose-Konfiguration mit Compose 5.8.0 und Docker Engine 29.1.3 unter
  Ubuntu/WSL2 geprüft. Kafka-/PostgreSQL-Digests über die Registry aufgelöst.
- Frischer rekursiver Checkout im Linux-Dateisystem mit Leerzeichen im Pfad:
  Python 3.12.16, 128 Tests bestanden, ein Windows-PowerShell-Test übersprungen;
  pip, Ruff und mypy erfolgreich. Alle 20 Vertrags-/Herkunfts-/Werkzeugtests bestanden.
- Die Wrapper-Tests prüfen auch native Windows PowerShell 5.1 und PowerShell
  7.6.9. Der reale Container-Stack läuft unter Ubuntu 22.04.5 in WSL2;
  ein Docker-Desktop- oder ARM-Nachweis wird nicht behauptet.

## Infrastruktur-Abnahme

Die vollständige Abnahme über `python3.12 -m scripts.validate_stack` wurde mit
den Standardports sowie mit abweichenden Ports 19092/15432/18081 erfolgreich
ausgeführt. Der zweite Lauf enthält die flüchtigen Kafka-Konfigurationsmounts.
Beide Läufe verwendeten eigene, vorher unbenutzte Compose-Projekte.

| Prüfung | Ergebnis |
|---|---|
| Processing-Build aus gespeichertem Service-Commit | erfolgreich; vorhandene Build-Schichten wiederverwendet |
| Kafka Produce/Consume | synthetischer Token unverändert zurückgelesen |
| Externer Kafka-Listener | Host-Metadatenabfrage bestätigt `localhost` und den jeweiligen Host-Port |
| PostgreSQL | authentifizierte TCP-Abfrage `SELECT 1` erfolgreich |
| Flink | genau ein registrierter TaskManager mit zwei Slots |
| Rollenidentität | identische Image-IDs, Python 3.12.15, PyFlink 2.2.1, Interpreterkonfiguration und sämtliche 29 JAR-Hashes |
| Isolierter Processing-Smoke-Test | JVM-Klassen und Kafka-/JDBC-Table-Planung erfolgreich |
| Wiederholte Initialisierung / wiederholter Start | erfolgreich; vorhandenes Topic erhalten |
| Vorhandenes Topic mit abweichender Partitionszahl | erwartungsgemäß abgelehnt, ohne Änderung/Löschung |
| Normaler Stop und erneuter Start | Kafka-Marker und SQL-Probetabelle mit unverändertem Inhalt erhalten |
| Getrennter Reset | Testcontainer, Netzwerk und benannte Testvolumes entfernt; keine Projektvolumes übrig |

Die Entwicklungsbefehle wurden außerdem über `dev.sh` und PowerShell 7 innerhalb
von WSL2 gegen die tatsächliche Docker-Engine geprüft. Native Windows-Tests
prüfen Argumente, Pfade mit Leerzeichen, Fehlercodes und das Überspringen einer
defekten `.venv`; der Reset ohne `--yes` scheitert vor dem ersten Docker-Aufruf.

## Tatsächlich verwendete Artefakte

Processing-Service-Commit: `edfcd03a7292d621482d04d1339eb3dd4c748229`.
JobManager und TaskManager verwendeten beide diese lokale Image-ID:

```text
sha256:d1d6834218c106b762089bc3c8d8e737c853e233cd10f46bffdca523d77103a4
```

Die gepinnte Flink-Basis ist
`sha256:c5124717afe3829cc2d7c9b538bfe0b9d66cae3107a174d8f0e0392abe6375b8`.
Die Kafka-/PostgreSQL-Manifest-Digests sind direkt in Compose fixiert und in der
[Stack-Anleitung](local-infrastructure.md#fixierte-images) aufgeführt. Die
gestarteten lokalen Image-IDs waren:

| Dienst | Image-ID |
|---|---|
| Kafka | `sha256:2805184e4ad28dac8f911174609d66b853b04d62005397097ab1ad88bc7da2df` |
| PostgreSQL | `sha256:107127087bab983e534546e8c30085e2ae04e4d805da656d1aee9340e5957fac` |

Bei unabhängigen Builds können Processing-Image-IDs wegen Build-Zeitstempeln
abweichen. Der relevante Nachweis ist die gleiche tatsächliche ID beider Rollen
innerhalb eines Laufs sowie die geprüften gelockten Laufzeitartefakte.

## Ressourcen, CI und Grenzen

Eine Momentaufnahme nach der zweiten Abnahme ergab ohne fachlichen Job:

| Dienst | Speicherbelegung laut `docker stats` |
|---|---|
| Kafka | etwa 322 MiB |
| PostgreSQL | etwa 29 MiB |
| JobManager | etwa 279 MiB |
| TaskManager | etwa 422 MiB |

Die WSL-Umgebung hatte etwa 15,5 GiB RAM verfügbar. Diese Leerlaufwerte sind
keine Obergrenze und kein Lasttest; der Build und spätere fachliche Jobs benötigen
zusätzliche Ressourcen. Die Empfehlung von vier Kernen, 8 GiB RAM für Docker/WSL
und 20 GiB freiem Speicher bleibt ein anfänglicher Entwicklungsrichtwert.

Die Hauptrepo-CI bestand für den ersten Implementierungsstand auf Push und PR
([PR-Lauf](https://github.com/vegedy/Soly/actions/runs/44520051996)). Der neue
Workflow **Local infrastructure** baut und prüft den Stack auf einem frischen
Ubuntu-Runner bei PRs, auf `main` und auf Abruf. Die tatsächlichen aktuellen
CI-Ergebnisse und Infrastruktur-Artefakte sind über
[PR #27](https://github.com/vegedy/Soly/pull/27) erreichbar; ein lokaler Lauf ersetzt
diesen unabhängigen Build nicht.

Rechnerbezogene Proxy-Anpassungen wurden ausschließlich außerhalb der
Repositories vorgenommen: zeitweilige Docker-Proxy-Konfiguration für Image-
Downloads und Host-Netzwerk mit den vordefinierten Docker-Proxy-Buildargumenten
für den lokalen Build. Die zeitweilige Dienstkonfiguration wurde entfernt.
Ein älterer Windows-Checkout enthielt noch CRLF-Shellskripte trotz LF-Vorgabe;
die versionierten Bytes wurden wiederhergestellt. Der frische Linux-Checkout
benötigte diese Korrektur nicht. Service-Commits, Vertragsartefakte, Locks und
Image-Pins blieben unverändert.

Noch nicht geprüft sind eine fachliche Pipeline, Datenbank-Ergebnissemantik,
Checkpoint-Recovery, produktive Hochverfügbarkeit und andere CPU-Architekturen.
