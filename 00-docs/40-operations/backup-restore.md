# Backups und Wiederherstellung

## Zweck

Die Daten des Stadtfest-Finders sichert das HomeLab mit ([ADR 0021](../25-adr/0021-backups.md), R16-US4). Es gibt keinen eigenen Backup-Dienst im Stack.

| Ebene | Was | Wann | Aufbewahrung | Wo |
|---|---|---|---|---|
| `pg_dump` | Datenbank `stadtfest` als gzip-SQL nach `${APPDATA}/stadtfest/backups/stadtfest-pg-<zeit>.sql.gz` | bei jedem `make backup`, vor dem Stoppen | 7 neueste | Server (NVMe) |
| kalter Btrfs-Snapshot | ganz `${APPDATA}` (u. a. `stadtfest/postgres`, `seaweedfs`, `redis`, `backups`) bei angehaltenen Stacks | `make backup` (Cron des HomeLab) | 7 neueste | `${COMPOSE_ROOT}/appdata-snapshots/` |
| Offsite (restic → pCloud) | neuester Snapshot, **ohne** `stadtfest/nominatim` (wird neu importiert) | wöchentlich, Mo 04:30 | 7 täglich / 4 wöchentlich / 6 monatlich | pCloud, clientseitig verschlüsselt |

Die Sicherungen enthalten personenbezogene Daten. Gelöschte Daten bleiben bis zu etwa **6 Monate** in älteren Offsite-Sicherungen ([Löschkonzept](../30-privacy/loeschkonzept.md#backups)).

## Voraussetzungen

- Backups des HomeLab eingerichtet (HomeLab `docs/OPERATIONS.md` §4: `make backup`, `make backup-offsite`, pCloud-Konto mit AV-Vertrag, restic-Passwort offline verwahrt)
- SSH-Zugang zum Server; der Stack `stadtfest` ist deployt ([deployment-komodo.md](deployment-komodo.md))

Für Stadtfest-Finder entstehen hier **keine neuen Werte**: Die Backup-Zugangsdaten gehören dem HomeLab (`${SECRETS}/restic-password`, `${SECRETS}/rclone.conf`).

## Schritte

### Prüfen, dass der Stack mitgesichert wird

1. `stadtfest` steht in `STACKS` im HomeLab-`Makefile` und in `scripts/backup-appdata.sh` (Reihenfolge beim Stoppen/Starten).
2. Nach dem nächsten `make backup`: `ls -1t /volume2/docker/appdata/stadtfest/backups/` zeigt eine neue Datei `stadtfest-pg-<zeit>.sql.gz`.

### Wiederherstellen: Datenbank aus dem Dump

Erst in eine **separate Datenbank** und prüfen, dann umschalten:

```bash
DUMP=/volume2/docker/appdata/stadtfest/backups/stadtfest-pg-<zeit>.sql.gz
docker exec stadtfest-postgres createdb -U stadtfest stadtfest_restore
gunzip -c "$DUMP" | docker exec -i stadtfest-postgres psql -U stadtfest -d stadtfest_restore -q -v ON_ERROR_STOP=1
docker exec stadtfest-postgres psql -U stadtfest -d stadtfest_restore -tAc 'select version_num from alembic_version'
```

Umschalten:

1. `docker stop stadtfest-api stadtfest-worker stadtfest-mcp`
2. Datenbanken tauschen:
   ```bash
   docker exec stadtfest-postgres psql -U stadtfest -d postgres -c 'ALTER DATABASE stadtfest RENAME TO stadtfest_broken'
   docker exec stadtfest-postgres psql -U stadtfest -d postgres -c 'ALTER DATABASE stadtfest_restore RENAME TO stadtfest'
   ```
3. In Komodo den Stack `stadtfest` deployen (`stadtfest-migrate` bringt das Schema auf den Stand des Images), danach Smoke-Test ([deployment-komodo.md](deployment-komodo.md#prüfung)).
4. **Löschungen nachholen:** Konten, die seit dem Sicherungszeitpunkt gelöscht wurden, erneut löschen ([Löschkonzept](../30-privacy/loeschkonzept.md#backups)).
5. Nach der Prüfung: `docker exec stadtfest-postgres dropdb -U stadtfest stadtfest_broken`.

### Wiederherstellen: Bilder aus dem Snapshot

Der Snapshot entsteht bei angehaltenem Stack und ist daher konsistent.

```bash
SNAP=/volume2/docker/appdata-snapshots/appdata-<zeit>
docker stop stadtfest-seaweedfs
sudo mv /volume2/docker/appdata/stadtfest/seaweedfs /volume2/docker/appdata/stadtfest/seaweedfs.broken
sudo cp -a "$SNAP/stadtfest/seaweedfs" /volume2/docker/appdata/stadtfest/seaweedfs
docker start stadtfest-seaweedfs
```

`seaweedfs.broken` nach der Prüfung entfernen. Datenbank und Bilder möglichst aus **demselben** Zeitpunkt wiederherstellen, sonst zeigen Feste auf fehlende bzw. verwaiste Bilder (verwaiste räumt `purge_images` auf).

### Wiederherstellen aus der Offsite-Kopie

Nach Verlust des Servers bzw. der Snapshots: `restic restore` des gewünschten Snapshots nach HomeLab `docs/OPERATIONS.md` §4, danach `stadtfest/postgres`, `stadtfest/seaweedfs` und `stadtfest/redis` aus dem wiederhergestellten Verzeichnis übernehmen (bzw. den Dump wie oben einspielen). `stadtfest/nominatim` ist nicht enthalten: leer lassen, der nächste Deploy importiert Deutschland neu (mehrere Stunden).

## Prüfung

- Jede `make backup`-Ausgabe enthält `-> …/stadtfest/backups/stadtfest-pg-<zeit>.sql.gz` (eine Zeile `WARN: … stadtfest` heißt: der Container lief nicht).
- **Probe-Wiederherstellung** mindestens einmal im Quartal: Dump in `stadtfest_restore` wie oben, Stichprobe (`select count(*) from event`), danach `dropdb … stadtfest_restore`.

**Geprobt am 16.10.2026** lokal mit dem HomeLab-Stack `stadtfest`: Probe-Konto angelegt, mit demselben `pg_dump`-Aufruf wie `make backup` gesichert, in `stadtfest_restore` eingespielt (`ON_ERROR_STOP`, PostGIS vorhanden, Migrationsstand `0013`, Probe-Konto da). Nach dem ersten Release in Produktion wiederholen und hier mit Datum eintragen.

## Rollback

- Fehlgeschlagene Wiederherstellung: die umbenannte Datenbank `stadtfest_broken` bzw. das Verzeichnis `seaweedfs.broken` zurückbenennen und den Stack deployen.
- Backups für den Stack aussetzen geht nur im HomeLab (Eintrag aus `STACKS`/`dump_pg` entfernen, PR); davon ist abzuraten.
