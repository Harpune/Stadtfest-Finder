# 0019 · Produktion als HomeLab-Stack `stadtfest`

- **Status:** angenommen
- **Datum:** 2026-10-16 (am selben Tag überarbeitet: erst eigener Stack mit eigenem Caddy, dann Einbindung ins vorhandene HomeLab)

## Kontext

R16 bringt den Stadtfest-Finder auf den eigenen Server in der EU. Auf diesem Server läuft bereits ein HomeLab ([github.com/Harpune/HomeLab](https://github.com/Harpune/HomeLab)) mit festen Regeln: ein Repo beschreibt alle Stacks, Komodo deployt sie per Klick aus dessen Klon, Images sind auf SemVer-Tags gepinnt und Renovate hebt sie, Secrets liegen nur in Komodos Variablenspeicher, öffentliche Dienste laufen über einen Cloudflare Tunnel zu einem Caddy im Docker-Netz `edge`, Daten liegen als Bind-Mounts unter `${APPDATA}`, Backups und Monitoring sind laborweit. Eigene Anwendungen werden nach `docs/CUSTOM-APPS.md` dort eingebunden („der Server zieht nur Images“).

Offen waren außerdem der Objektspeicher in Produktion ([ADR 0007](0007-objektspeicher-seaweedfs.md) nannte SeaweedFS nur als Kandidaten) und der produktive Push-Weg ([ADR 0016](0016-benachrichtigungen-und-push.md)).

## Entscheidung

1. **Stack im HomeLab:** `stacks/stadtfest/compose.yaml` mit `stadtfest-edge`, `-api`, `-worker`, `-mcp`, `-migrate`, `-postgres` (PostGIS), `-redis`, `-nominatim`, `-searxng`, `-seaweedfs`. Komodo-Ressource mit `[[STADTFEST_*]]`-Variablen. Dieses Repo enthält keine Produktions-Compose-Datei mehr, nur den Umgebungsvertrag des Backends ([`infra/komodo-environment.example`](../../infra/komodo-environment.example), im CI gegen die Settings geprüft).
2. **Images aus diesem Repo:** `stadtfest-backend` (API, Worker, Migration), `stadtfest-mcp`, `stadtfest-edge` und `stadtfest-searxng`, alle mit demselben Tag. Ein Tag `vX.Y.Z` baut sie als `X.Y.Z`; Renovate im HomeLab hebt alle vier in einem PR; deployt wird von Hand in Komodo. Rollback = vorheriger Tag.
3. **`stadtfest-edge` als anwendungseigener Proxy** (Caddy-Image aus `infra/edge/`): einziger Container im Netz `edge`. Der HomeLab-Caddy leitet vier Hosts unverändert dorthin; `stadtfest-edge` routet nach Host, gibt vom Objektspeicher nur `GET`/`HEAD` auf `public/` und signierte `PUT` auf `uploads/` frei und liefert die Deep-Link-Seiten, `assetlinks.json`, `apple-app-site-association`, Impressum und Datenschutzerklärung aus (Werte per Template aus der Umgebung). Das Routing gehört hierher, weil es an Pfade und Dateien der App gebunden ist.
4. **Hosts eine Ebene unter der Domain:** `stadtfest.`, `stadtfest-api.`, `stadtfest-mcp.`, `stadtfest-bilder.herderstreet.de`. Das kostenlose Cloudflare-Zertifikat deckt nur `*.herderstreet.de` ab.
5. **SeaweedFS selbst gehostet** (wie lokal und in Tests). Die S3-Identität erzeugt der Container beim Start aus der Umgebung (kein Secret auf der Platte): Backend-Identität nur auf den Bucket, anonymes Lesen nur unter `public/`.
6. **Konfiguration ohne Dateien:** SearXNG-Einstellungen im Image `stadtfest-searxng`; APNs- und FCM-Schlüssel als base64 in Komodo-Secrets (`APNS_KEY_BASE64`, `FCM_CREDENTIALS_BASE64`; Dateipfade bleiben für lokal).
7. **Migrationen als Dienst `stadtfest-migrate`** (`alembic upgrade head`); API, Worker und MCP-Server starten erst nach Exit 0. Nur rückwärtskompatible Migrationen (Expand/Contract), damit ein Rollback ohne Rückmigration geht.
8. **Produktive Standards:** `LLM_PROVIDER=mistral` (Ollama des HomeLab möglich), `WEB_SEARCH_PROVIDER=searxng`, `PUSH_PROVIDER=direct` (kein Expo als zusätzlicher Verarbeiter).

## Konsequenzen

- Anleitung mit der Herkunft jedes Werts: [deployment-komodo.md](../40-operations/deployment-komodo.md). Die GHCR-Pakete müssen öffentlich sein (das HomeLab zieht anonym).
- Kein automatisches Deployment nach einem Merge; `make smoke` prüft nach dem Deploy.
- Öffentlicher Eingang über Cloudflare ([ADR 0022](0022-eingang-cloudflare-tunnel.md)), Backups ([ADR 0021](0021-backups.md)) und Logs ([ADR 0020](0020-beobachtbarkeit.md)) kommen aus dem HomeLab.
- Der Server braucht für Nominatim (Deutschland) rund 100 GB und bis zu 12 GB RAM; der Server hat 64 GB.

## Verworfene Alternativen

- **Eigener Stack mit eigenem Caddy auf 80/443 und Deploy per GitHub-Workflow über die Komodo-API:** kollidiert mit dem vorhandenen Caddy und mit der HomeLab-Regel, dass Deploys von Hand erfolgen.
- **Routen direkt im HomeLab-Caddyfile statt `stadtfest-edge`:** Deep-Link-Dateien und Pfadregeln der App lägen dann im HomeLab und müssten bei jedem App-Release dort mitgeändert werden.
- **S3-Dienst in der EU:** ein weiterer Auftragsverarbeiter mit Bilddaten.
- **Zwei Ebenen (`api.stadtfest.…`):** bräuchte Cloudflare Advanced Certificate Manager.
