# 0021 · Backups mit restic auf eine Hetzner Storage Box

- **Status:** angenommen
- **Datum:** 2026-10-16

## Kontext

R16-US4 verlangt ein tägliches, verschlüsseltes Backup von PostgreSQL und Objektspeicher an ein EU-Ziel mit 30 Tagen Aufbewahrung und eine geprobte Wiederherstellung. Backups enthalten personenbezogene Daten.

## Entscheidung

1. **Eigenes Image `stadtfest-backup`** (`infra/backup`, gebaut im Release-Workflow, gleicher Tag wie das Backend): `postgres:17-alpine` mit `pg_dump`, **restic** und **rclone** (beide aus den offiziellen Images kopiert). Der Container läuft als Nutzer `backup` (uid 10001) und startet die Sicherung täglich um `BACKUP_TIME` (Standard 02:30 Uhr, vor den Aufräum-Jobs ab 03:30 Uhr).
2. **Ziel:** restic-Repository auf einer **Hetzner Storage Box** (Rechenzentrum in Deutschland) über SFTP. restic verschlüsselt auf dem eigenen Server (AES-256), Hetzner sieht nur verschlüsselte Blöcke. Das Repository-Passwort liegt als Komodo-Secret und zusätzlich offline.
3. **Datenbank:** `pg_dump --format=custom` geht direkt in restic (`--stdin-from-command`), es entsteht keine unverschlüsselte Kopie auf der Platte.
4. **Objektspeicher:** rclone spiegelt den Bucket über die S3-API in den Cache des Containers, restic sichert den Spiegel. Eine Kopie der laufenden SeaweedFS-Dateien ist beim Wiederherstellungstest gescheitert (der Bucket fehlte danach); die S3-API liefert einen konsistenten Stand und erlaubt die Wiederherstellung in jeden S3-Speicher.
5. **Aufbewahrung:** `restic forget --keep-within 30d --prune` nach jeder Sicherung, sonntags zusätzlich `restic check`.
6. **Überwachung:** JSON-Logzeilen `backup_succeeded`/`backup_failed`; Grafana alarmiert, wenn 26 Stunden lang keine erfolgreiche Sicherung kam ([ADR 0020](0020-beobachtbarkeit.md)). Der Healthcheck des Containers prüft dasselbe.

## Datenschutz

- Hetzner Online GmbH ist Auftragsverarbeiter (AV-Vertrag nötig), Standort Deutschland.
- Gelöschte Daten (z. B. nach einer Kontolöschung) bleiben bis zu 30 Tage in älteren Sicherungen und verschwinden danach mit dem Ablauf der Aufbewahrung. Eine Wiederherstellung spielt Löschungen seit dem Sicherungszeitpunkt erneut ein ([Löschkonzept](../30-privacy/loeschkonzept.md#backups)).

## Konsequenzen

- Der Spiegel des Buckets belegt im Volume `backup-cache` noch einmal den Platz der Bilder.
- Der Wiederherstellungsablauf ist in [backup-restore.md](../40-operations/backup-restore.md) beschrieben und wurde lokal mit dem Stack geprobt; in Produktion wird er nach der Einrichtung einmal wiederholt.

## Verworfene Alternativen

- **EU-S3-Bucket als restic-Ziel:** genauso möglich, aber ein zweiter Speicherdienst neben der Storage Box ohne Vorteil.
- **Lokale Platte oder NAS:** kein externer Verarbeiter, aber keine Kopie außer Haus (Brand, Diebstahl).
- **BorgBackup:** vergleichbar, aber ohne S3-/stdin-Komfort und mit Server-Komponente auf dem Ziel.
- **Kopie des SeaweedFS-Volumes:** im Test nicht wiederherstellbar (siehe oben).
