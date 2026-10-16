# Backups einrichten und wiederherstellen

## Zweck

Der Dienst `backup` (Image `stadtfest-backup`, R16-US4, [ADR 0021](../25-adr/0021-backups.md)) sichert täglich um 02:30 Uhr

- die Datenbank (`pg_dump`, direkt in restic, keine unverschlüsselte Kopie) und
- den Bilder-Bucket (Spiegel über die S3-API mit rclone)

verschlüsselt mit restic auf eine **Hetzner Storage Box** (Deutschland). Aufbewahrung 30 Tage (`BACKUP_KEEP_WITHIN`), sonntags zusätzlich `restic check`. Die Sicherungen enthalten personenbezogene Daten; zur Wirkung von Löschungen siehe [Löschkonzept](../30-privacy/loeschkonzept.md#backups).

## Voraussetzungen

- Hetzner-Konto, AV-Vertrag mit Hetzner abgeschlossen ([Auftragsverarbeiter](../30-privacy/auftragsverarbeiter.md))
- Shell auf dem Heimserver, Zugriff auf Komodo (Secrets, Terminal des Stacks)
- Stack nach [deployment-komodo.md](deployment-komodo.md) eingerichtet

## Schritte

### Einrichten

1. **Storage Box bestellen** (z. B. BX11, Standort Falkenstein oder Nürnberg). In der Hetzner-Konsole *SSH-Support* und *Externe Erreichbarkeit* aktivieren.
2. **SSH-Schlüssel** nur für das Backup erzeugen und hinterlegen (Port 23):
   ```bash
   ssh-keygen -t ed25519 -N "" -C stadtfest-backup -f id_ed25519
   cat id_ed25519.pub | ssh -p 23 uXXXXXX@uXXXXXX.your-storagebox.de install-ssh-key
   ssh-keyscan -p 23 uXXXXXX.your-storagebox.de > known_hosts
   ```
3. **Dateien ablegen** in `/etc/stadtfest/secrets/backup-ssh/` (`id_ed25519`, `known_hosts`) und eine `config`:
   ```
   Host storagebox
     HostName uXXXXXX.your-storagebox.de
     User uXXXXXX
     Port 23
     IdentityFile ~/.ssh/id_ed25519
   ```
   Rechte wie in [deployment-komodo.md](deployment-komodo.md), Schritt 2 (`root:10001`, keine Rechte für andere).
4. **Ordner** auf der Box anlegen: `ssh storagebox mkdir -p stadtfest` (vom Server aus mit der config oben, oder per SFTP).
5. **Repository-Passwort** erzeugen (`openssl rand -hex 32`), als Komodo-Secret `STADTFEST_RESTIC_PASSWORD` hinterlegen und **zusätzlich offline** aufbewahren (Passwortmanager). Ohne Passwort sind die Sicherungen wertlos.
6. In der Stack-Umgebung `RESTIC_REPOSITORY=sftp:storagebox:/stadtfest/restic` setzen, Stack deployen.
7. **Repository anlegen** (einmalig): `docker compose exec backup backup.sh init`
8. **Erste Sicherung** sofort: `docker compose exec backup backup.sh run`

### Wiederherstellen: Datenbank

Erst in eine **separate Datenbank** wiederherstellen und prüfen, dann umschalten:

```bash
docker compose exec backup restic snapshots --tag postgres
docker compose exec backup createdb stadtfest_restore
docker compose exec -T backup sh -c 'restic dump --host stadtfest --tag postgres latest stadtfest.dump | pg_restore --no-owner --no-privileges -d stadtfest_restore'
docker compose exec backup psql -d stadtfest_restore -c 'select version_num from alembic_version'
```

Statt `latest` geht eine Snapshot-ID aus `restic snapshots`. Zum Umschalten:

1. `api`, `worker`, `mcp` in Komodo stoppen.
2. Alte Datenbank umbenennen, wiederhergestellte übernehmen:
   ```bash
   docker compose exec backup psql -d postgres -c 'ALTER DATABASE stadtfest RENAME TO stadtfest_broken'
   docker compose exec backup psql -d postgres -c 'ALTER DATABASE stadtfest_restore RENAME TO stadtfest'
   ```
3. Stack deployen (`migrate` bringt das Schema auf den Stand des Images), Smoke-Test.
4. **Löschungen nachholen:** Konten, die seit dem Sicherungszeitpunkt gelöscht wurden, erneut löschen (Löschkonzept).
5. `stadtfest_broken` nach der Prüfung löschen (`DROP DATABASE`).

### Wiederherstellen: Bilder

```bash
docker compose exec backup restic restore --host stadtfest --tag objects latest --target /tmp/restore
docker compose exec backup rclone copy /tmp/restore/cache/objects 'objects:stadtfest-images'
```

Bei einem leeren SeaweedFS vorher den Bucket anlegen ([objektspeicher.md](objektspeicher.md)). `rclone copy` überschreibt nichts Neueres und löscht nichts.

## Prüfung

- Log-Ereignis `backup_succeeded` jeden Tag (Grafana, Alarm „Backup fehlt“ nach 26 Stunden, [monitoring.md](monitoring.md)); der Container ist *healthy*.
- `docker compose exec backup restic snapshots` zeigt je Tag einen Snapshot `postgres` und `objects`, keiner älter als 30 Tage.
- **Probe-Wiederherstellung** (mindestens einmal im Quartal): Datenbank in `stadtfest_restore` wie oben, Stichprobe (`select count(*) from event`), danach `DROP DATABASE stadtfest_restore`.

**Geprobt am 16.10.2026** lokal mit dem Stack aus `infra/compose.yaml`: Probe-Konto angelegt, gesichert, gelöscht, aus dem Dump in `stadtfest_restore` zurückgeholt (Migrationsstand `0013`); ein Probe-Bild gesichert und in ein **leeres** SeaweedFS mit neuem Bucket wiederhergestellt und gelesen. Eine Kopie der SeaweedFS-Dateien statt der S3-API ließ sich dabei **nicht** wiederherstellen (Bucket fehlte), daher der S3-Spiegel. Nach der Einrichtung in Produktion die Probe einmal wiederholen und hier mit Datum eintragen.

## Rollback

- Backup aussetzen: Dienst `backup` in Komodo stoppen (Alarm „Backup fehlt“ beachten).
- Kompromittierter SSH-Schlüssel: in der Hetzner-Konsole entfernen, neuen Schlüssel nach Schritt 2 erzeugen.
- Kompromittiertes Repository-Passwort: `restic key add` mit neuem Passwort, alten Schlüssel mit `restic key remove <id>` entfernen, Komodo-Secret ersetzen.
