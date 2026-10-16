# Produktion mit Komodo deployen

## Zweck

Der Produktionsstack (`infra/compose.yaml`) läuft auf dem Heimserver (EU) und wird von Komodo deployt (R16-US1, [ADR 0019](../25-adr/0019-produktionsstack.md)). Ein Merge auf `main` baut die Images in GHCR (`release.yml`), danach setzt `deploy.yml` den Image-Tag in Komodo, startet das Deployment und prüft es mit dem Smoke-Test. Rollback = Deployment mit dem vorherigen Tag.

| Dienst | Aufgabe | öffentlich |
|---|---|---|
| `caddy` | TLS, Routen für `api.`, `mcp.`, `bilder.` und die Deep-Link-Domain | 80/443 |
| `migrate` | `alembic upgrade head`, einmalig vor API, Worker und MCP | – |
| `api`, `worker`, `mcp` | Backend (Image `stadtfest-backend` bzw. `stadtfest-mcp`) | über Caddy |
| `postgres`, `redis`, `seaweedfs`, `nominatim`, `searxng` | Daten, Queue/Cache, Bilder, Geocoding, Web-Suche | nein |
| `backup` | tägliche Sicherung ([backup-restore.md](backup-restore.md)) | nein |
| `loki`, `alloy`, `grafana` | Logs und Alarme ([monitoring.md](monitoring.md)) | Grafana nur `127.0.0.1` |

## Voraussetzungen

- Heimserver mit Docker Engine und Compose-Plugin, **mindestens 16 GB RAM, 4 Kerne, 150 GB SSD**
- Komodo Core und Periphery auf dem Server ([komo.do](https://komo.do)), Komodo Core per HTTPS erreichbar (für GitHub Actions)
- DNS-Zugriff für `herderstreet.de`, Ports 80 und 443 vom Internet auf den Server weitergeleitet
- Admin-Rechte im GitHub-Repository (Variablen, Secrets, Environment `production`)
- Erledigt: [Zitadel](zitadel.md), [LLM-Anbieter](llm-anbieter.md), [Push APNs/FCM](push-apns-fcm.md), [Deep Links](deep-links-domain.md); für die Bilder [Objektspeicher](objektspeicher.md)

## Schritte

### 1. DNS

A- bzw. AAAA-Einträge auf die öffentliche IP des Servers (bei dynamischer IP über den vorhandenen DynDNS-Mechanismus):

| Name | Zweck |
|---|---|
| `stadtfest.herderstreet.de` | Deep Links, Impressum, Datenschutz |
| `api.stadtfest.herderstreet.de` | REST-API |
| `mcp.stadtfest.herderstreet.de` | MCP-Server |
| `bilder.stadtfest.herderstreet.de` | öffentliche Festbilder und signierte Uploads |

### 2. Secret-Dateien auf dem Server

```bash
sudo mkdir -p /etc/stadtfest/secrets/push /etc/stadtfest/secrets/backup-ssh
# APNs-Schlüssel und FCM-Dienstkonto (push-apns-fcm.md)
sudo cp AuthKey_XXXX.p8 /etc/stadtfest/secrets/push/apns.p8
sudo cp firebase-service-account.json /etc/stadtfest/secrets/push/fcm.json
# SeaweedFS-Identitäten aus der Vorlage infra/prod/seaweedfs/s3.example.json (objektspeicher.md)
sudo cp s3.json /etc/stadtfest/secrets/seaweedfs-s3.json
# SSH-Schlüssel, known_hosts und config für die Storage Box (backup-restore.md)
sudo chown -R root:10001 /etc/stadtfest/secrets
sudo chmod -R u=rwX,g=rX,o= /etc/stadtfest/secrets
```

Die Backend-Container laufen als uid 10001 und lesen die Dateien über die Gruppe. **Nichts davon kommt ins Repo.**

### 3. Komodo: Variablen und Secrets

Unter *Settings → Variables* (Secrets als „secret“ markieren, Werte mit `openssl rand -hex 32` erzeugen):

| Variable | Inhalt |
|---|---|
| `STADTFEST_IMAGE_TAG` | erster Tag, z. B. `sha-<commit>` des letzten `main`-Builds (setzt danach der Deploy-Workflow) |
| `STADTFEST_POSTGRES_PASSWORD`, `STADTFEST_NOMINATIM_DB_PASSWORD` | Datenbankpasswörter |
| `STADTFEST_S3_SECRET_ACCESS_KEY` | Secret der Backend-Identität aus `seaweedfs-s3.json` |
| `STADTFEST_IDP_ADMIN_TOKEN` | PAT des Zitadel-Service-Users |
| `STADTFEST_LLM_API_KEY` | Mistral-Schlüssel |
| `STADTFEST_SEARXNG_SECRET` | SearXNG-Secret |
| `STADTFEST_RESTIC_PASSWORD` | Passwort des Backup-Repositorys (zusätzlich offline aufbewahren) |
| `STADTFEST_GRAFANA_ADMIN_PASSWORD` | Grafana-Admin |

### 4. Komodo: Stack anlegen

1. *Stacks → New Stack* `stadtfest`, Server = Heimserver.
2. *Source:* Git-Repository `Harpune/Stadtfest-Finder`, Branch `main`, **Run Directory** `infra`, **File Paths** `compose.yaml`.
3. *Environment:* Inhalt von [`infra/komodo-environment.example`](../../infra/komodo-environment.example) einfügen und die `REPLACE_WITH_…`-Werte ersetzen. Die `[[…]]`-Verweise bleiben stehen, Komodo setzt die Variablen aus Schritt 3 ein. Komodo schreibt die Umgebung als `.env` ins Run Directory; die Backend-Dienste lesen sie als `env_file`.
4. *Ignore Services:* `migrate` (endet absichtlich nach der Migration).
5. *Auto Update* und *Poll for Updates* **aus**: Versionen kommen nur über `STADTFEST_IMAGE_TAG`.
6. GHCR: Sind die Pakete privat, unter *Settings → Registry Accounts* einen GitHub-Nutzer mit Token (`read:packages`) für `ghcr.io` hinterlegen und im Stack auswählen.

### 5. Erstes Deployment

1. *Deploy* im Stack. Reihenfolge: Datenbanken → `migrate` → `api`, `worker`, `mcp` → `caddy`.
2. **Nominatim** importiert beim ersten Start Deutschland (mehrere Stunden, [nominatim.md](nominatim.md)). Bis dahin antwortet `/v1/geocode*` mit `503` und `search_events` im MCP-Server mit einem Tool-Fehler; die Festsuche läuft.
3. Bucket anlegen und Lifecycle-Regel setzen ([objektspeicher.md](objektspeicher.md)).
4. Backup-Repository einmalig anlegen: `docker compose exec backup backup.sh init` (im Komodo-Terminal des Stacks).

### 6. GitHub: automatisches Deployment

1. *Settings → Environments → New environment* `production` (optional mit Required reviewers).
2. *Settings → Secrets and variables → Actions*:
   - Variablen: `KOMODO_URL` (z. B. `https://komodo.herderstreet.de`), `KOMODO_STACK=stadtfest`, `API_URL=https://api.stadtfest.herderstreet.de`, `MCP_URL=https://mcp.stadtfest.herderstreet.de`
   - Secrets (im Environment `production`): `KOMODO_API_KEY`, `KOMODO_API_SECRET` (Komodo → *Profile → API Keys*, Nutzer mit Schreibrecht auf Variable und Stack)
3. Ab jetzt läuft nach jedem Merge auf `main`: `Release images` → `Deploy` (Tag `sha-<commit>`) → Smoke-Test.

### Migrationen bei laufendem Betrieb (Expand/Contract)

Während eines Deployments läuft kurz die alte API gegen das neue Schema. Deshalb:

1. **Expand:** neue Spalten nullable oder mit Default, neue Tabellen; alte Spalten bleiben. Code liest und schreibt beides, wo nötig.
2. Deployen, prüfen.
3. **Contract** in einem späteren Release: alte Spalten entfernen, `NOT NULL` setzen.

Nie Spalten in derselben Migration umbenennen oder löschen, die der laufende Code noch nutzt. So bleibt jeder Rollback auf den vorherigen Tag ohne Rückmigration möglich.

## Prüfung

```bash
make smoke API_URL=https://api.stadtfest.herderstreet.de MCP_URL=https://mcp.stadtfest.herderstreet.de
```

Erwartet: fünf Zeilen mit `ok` (Health live/ready, `GET /v1/categories`, `GET /v1/events`, MCP `search_events`). Zusätzlich:

- Komodo zeigt alle Dienste *healthy*, `migrate` *exited (0)*.
- `curl -sI https://stadtfest.herderstreet.de/impressum/` liefert `200`.
- Der Workflow `Deploy` ist grün und nennt den deployten Tag.

## Rollback

1. *Actions → Deploy → Run workflow*, `tag` = vorheriger Tag (aus dem letzten grünen Deploy-Lauf oder GHCR).
2. Der Workflow setzt `STADTFEST_IMAGE_TAG`, deployt und prüft. Wegen Expand/Contract läuft der alte Code gegen das neue Schema; eine Rückmigration (`alembic downgrade`) ist nur nötig, wenn eine Migration ausnahmsweise nicht rückwärtskompatibel war, und dann vorher ein Backup zurückspielen ([backup-restore.md](backup-restore.md)).
3. Ohne GitHub: in Komodo die Variable `STADTFEST_IMAGE_TAG` von Hand setzen und *Deploy* drücken.

**Geprobt:** lokal mit dem Stack aus `infra/compose.yaml` (Images `:local`, Migration → API/Worker/MCP gesund, Smoke-Test). In Produktion nach dem ersten Deployment einmal ein Rollback auf den vorherigen Tag durchspielen und hier mit Datum vermerken.
