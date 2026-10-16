# 0019 · Produktionsstack: SeaweedFS, Caddy und Deployment mit festem Image-Tag über Komodo

- **Status:** angenommen
- **Datum:** 2026-10-16

## Kontext

R16 bringt den Stadtfest-Finder auf den eigenen Server in der EU. Offen waren:

- der Objektspeicher in Produktion ([ADR 0007](0007-objektspeicher-seaweedfs.md) nannte SeaweedFS nur als Kandidaten),
- der Reverse Proxy mit TLS (Caddy oder Traefik),
- wie Komodo „eine festgelegte Version“ deployt und wie Migrationen vor der neuen API-Version laufen,
- der produktive Push-Weg ([ADR 0016](0016-benachrichtigungen-und-push.md) lässt `expo` und `direct` zu).

## Entscheidung

1. **SeaweedFS selbst gehostet** (Image `chrislusf/seaweedfs`, feste Version) auf dem Heimserver, wie lokal und in den Tests. Identitäten stehen in einer Datei außerhalb des Repos (`$SECRETS_DIR/seaweedfs-s3.json`, Vorlage `infra/prod/seaweedfs/s3.example.json`): eine Backend-Identität nur für den Bucket, eine Admin-Identität für die Einrichtung, anonym lesbar nur `public/`.
2. **Caddy** als einziger Dienst mit offenen Ports (80/443), Konfiguration `infra/caddy/Caddyfile`:
   - `api.…` → API, `mcp.…` → MCP-Server (Streaming ohne Puffer),
   - `bilder.…` → SeaweedFS, aber nur `GET`/`HEAD` auf `/<bucket>/public/*` und signierte `PUT` auf `/<bucket>/uploads/*` (höchstens 11 MB); der Rest der S3-API bleibt intern,
   - die Deep-Link-Domain mit Fallback-Seiten, `assetlinks.json`, `apple-app-site-association`, Impressum, Datenschutzerklärung und Nutzungsbedingungen. Fingerabdrücke, Team-ID und Impressumsangaben kommen per Caddy-Templates aus der Stack-Umgebung, nicht aus dem Repo.
   - Automatisches TLS (Let's Encrypt), keine Access-Logs.
3. **Ein Image-Tag für alle eigenen Images** (`stadtfest-backend`, `stadtfest-mcp`, `stadtfest-backup`): `sha-<commit>` von `main` oder eine SemVer-Version. Der Tag steht in der Komodo-Variable `STADTFEST_IMAGE_TAG`. Der Workflow `deploy.yml` setzt sie nach erfolgreichem Release über die Komodo-API, startet `DeployStack`, wartet auf das Ergebnis und führt den Smoke-Test aus. Rollback = derselbe Workflow mit dem vorherigen Tag.
4. **Migrationen als eigener Dienst `migrate`** (`alembic upgrade head`, einmalig). API, Worker und MCP-Server starten erst, wenn er mit 0 endet. Bei laufendem Betrieb sind nur rückwärtskompatible Migrationen erlaubt (Expand/Contract, siehe [deployment-komodo.md](../40-operations/deployment-komodo.md)); so bleibt ein Rollback auf das vorherige Image ohne Rückmigration möglich.
5. **Produktive Standards:** `LLM_PROVIDER=mistral` (oder `ollama`), `WEB_SEARCH_PROVIDER=searxng`, `PUSH_PROVIDER=direct` (kein Expo als zusätzlicher Verarbeiter). Interne Adressen (Datenbank, Redis, Nominatim, SearXNG, S3) und `ENV=prod`/`LOG_FORMAT=json` setzt `infra/compose.yaml`; alles andere steht in der Stack-Umgebung in Komodo (Vorlage `infra/komodo-environment.example`, im CI gegen die Settings geprüft).

## Konsequenzen

- Kein zusätzlicher Auftragsverarbeiter für Bilder; Bilder liegen auf dem eigenen Server und sind im täglichen Backup ([ADR 0021](0021-backups.md)).
- Der Heimserver braucht für den ganzen Stack mindestens 16 GB RAM (Nominatim bis 12 GB) und etwa 150 GB SSD.
- Komodo Core muss für GitHub Actions per HTTPS erreichbar sein (API-Schlüssel nur für Variable und Deploy).
- `make infra-check` und der CI-Job „Production stack“ prüfen Compose-Datei und Caddyfile mit der Vorlage.

## Verworfene Alternativen

- **S3-Dienst in der EU** (z. B. Hetzner Object Storage, Scaleway): weniger Betrieb auf dem Heimserver, aber ein weiterer Auftragsverarbeiter mit Bilddaten.
- **Traefik:** Routing über Container-Labels, aber mehr Konfiguration für statische Dateien und Templates; die Deep-Link-Seite lief schon mit Caddy.
- **`latest`-Tag mit Auto-Update in Komodo:** kein reproduzierbarer Stand, kein gezielter Rollback.
- **Migrationen beim Start der API:** mehrere Replikate oder Neustarts würden gleichzeitig migrieren; ein Fehler bliebe im API-Log versteckt.
