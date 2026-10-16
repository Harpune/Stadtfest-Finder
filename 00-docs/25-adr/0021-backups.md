# 0021 · Backups über das HomeLab

- **Status:** angenommen
- **Datum:** 2026-10-16 (am selben Tag überarbeitet: statt eigenem restic-Dienst mit Hetzner Storage Box die Backups des HomeLab)

## Kontext

R16-US4 verlangt ein tägliches, verschlüsseltes Backup von Datenbank und Objektspeicher an ein EU-Ziel, eine geprobte Wiederherstellung und eine Aussage, wie Löschungen gegenüber Backups wirken. Das HomeLab sichert bereits alle Stacks: `pg_dump` der Postgres-Datenbanken, kalter Btrfs-Snapshot von `${APPDATA}` bei angehaltenen Stacks (7 neueste) und wöchentlich restic → pCloud (7 täglich / 4 wöchentlich / 6 monatlich, clientseitig verschlüsselt).

## Entscheidung

1. **Kein eigener Backup-Dienst.** Der Stack `stadtfest` steht in den Stack-Listen von `make backup`; `scripts/backup-appdata.sh` schreibt vor dem Snapshot `pg_dump` der Datenbank `stadtfest` nach `${APPDATA}/stadtfest/backups`.
2. **Objektspeicher über den kalten Snapshot:** Er entsteht bei angehaltenem Stack und ist damit konsistent. (Eine Kopie der *laufenden* SeaweedFS-Dateien war im ersten Wiederherstellungstest nicht brauchbar.)
3. **Nominatim ausgenommen** von der Offsite-Kopie (~100 GB, aus Geofabrik neu importierbar).
4. **Aufbewahrung wie im HomeLab:** lokal 7 Snapshots bzw. Dumps, offsite bis zu 6 Monate. Das [Löschkonzept](../30-privacy/loeschkonzept.md#backups) beschreibt, dass gelöschte Daten bis zu dieser Frist in Sicherungen bleiben.

## Datenschutz

- pCloud (pCloud AG, Schweiz) ist Auftragsverarbeiter des HomeLab; die Daten sind vor dem Hochladen verschlüsselt. Speicherregion des Kontos (EU/Luxemburg) prüfen ([Auftragsverarbeiter](../30-privacy/auftragsverarbeiter.md)).
- Nach einer Wiederherstellung sind Löschungen seit dem Sicherungszeitpunkt erneut auszuführen ([backup-restore.md](../40-operations/backup-restore.md)).

## Konsequenzen

- Während `make backup` ist der Stadtfest-Finder einige Minuten nicht erreichbar (Kaltsicherung des ganzen HomeLab).
- Wiederherstellung und Probe: [backup-restore.md](../40-operations/backup-restore.md).

## Verworfene Alternativen

- **Eigenes Image mit restic → Hetzner Storage Box, 30 Tage** (erste Fassung dieses ADR): doppelte Sicherung neben dem HomeLab, zusätzlicher Verarbeiter.
- **HomeLab-Backup, aber Stadtfest-Daten aus der 6-Monats-Kopie ausnehmen und separat 30 Tage halten:** mehr Sonderfälle im HomeLab-Skript; die längere Frist ist im Löschkonzept begründet.
