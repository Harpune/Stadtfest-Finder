# Produktion im HomeLab (Komodo) betreiben

## Zweck

Der Stadtfest-Finder läuft als Stack `stadtfest` im HomeLab ([github.com/Harpune/HomeLab](https://github.com/Harpune/HomeLab), `stacks/stadtfest/`) auf dem eigenen Server in der EU ([ADR 0019](../25-adr/0019-produktionsstack.md)). Dieses Repo liefert nur Images und den Umgebungsvertrag; Stack, Reverse Proxy, Backups und Logs gehören dem HomeLab.

**Ablauf eines Releases:** Git-Tag `vX.Y.Z` hier → `release.yml` baut `stadtfest-backend`, `stadtfest-mcp`, `stadtfest-edge`, `stadtfest-searxng` mit Tag `X.Y.Z` in GHCR → Renovate im HomeLab öffnet einen PR, der alle vier Pins hebt → Merge → in Komodo *Deploy* (von Hand, wie jeder Stack im HomeLab) → `stadtfest-migrate` migriert, danach starten API, Worker und MCP → Smoke-Test. Rollback = vorherigen Tag deployen.

**Weg einer Anfrage:** App bzw. MCP-Client → Cloudflare Tunnel → Caddy des HomeLab (TLS, `*.herderstreet.de`) → `stadtfest-edge` (Routing nach Host) → API, MCP-Server, Objektspeicher oder statische Seiten.

| Host | Ziel | Zweck |
|---|---|---|
| `stadtfest.herderstreet.de` | `stadtfest-edge` → statische Dateien | Deep Links, `assetlinks.json`, `apple-app-site-association`, Impressum, Datenschutz, Nutzungsbedingungen |
| `stadtfest-api.herderstreet.de` | → `stadtfest-api:8000` | REST-API der App |
| `stadtfest-mcp.herderstreet.de` | → `stadtfest-mcp:8001` | MCP-Server (`/mcp`) |
| `stadtfest-bilder.herderstreet.de` | → `stadtfest-seaweedfs:8333` | nur Lesen von `public/` und signierte Uploads nach `uploads/` |

Die Hosts liegen eine Ebene unter der Domain, weil das kostenlose Cloudflare-Zertifikat nur `*.herderstreet.de` abdeckt. Beispiele gehen von `DOMAIN=herderstreet.de` im HomeLab aus.

## Voraussetzungen

- Zugriff auf den Server per SSH, auf Komodo (`https://komodo.herderstreet.de`, Admin-Konto für Variablen), auf das Cloudflare-Dashboard (Zone und Tunnel) und Admin-Rechte in beiden GitHub-Repos
- Erledigt, weil ihre Werte hier gebraucht werden: [Zitadel](zitadel.md), [LLM-Anbieter](llm-anbieter.md), [Push APNs/FCM](push-apns-fcm.md). Für die Rechtstexte: Impressumsangaben.
- Der HomeLab-PR mit `stacks/stadtfest/` ist gemergt und auf dem Server gezogen (`git pull` in `/volume2/docker`).

## Schritte

### 1. Images öffentlich machen und ersten Release bauen

1. In diesem Repo einen Tag setzen: `git tag v1.0.0 && git push origin v1.0.0`. `release.yml` baut die vier Images mit Tag `1.0.0`.
2. GitHub → Profil → *Packages* → je Paket (`stadtfest-backend`, `stadtfest-mcp`, `stadtfest-edge`, `stadtfest-searxng`) → *Package settings* → *Change visibility* → **Public**. Neue GHCR-Pakete sind privat; das HomeLab zieht anonym (wie bei `feststadt`). Die Images enthalten keine Secrets.
3. Prüfen: `docker manifest inspect ghcr.io/harpune/stadtfest-backend:1.0.0` liefert ein Manifest.
4. Der Pin im HomeLab (`stacks/stadtfest/compose.yaml`) steht auf `1.0.0`. Spätere Versionen hebt Renovate per PR.

### 2. Cloudflare Tunnel

Cloudflare-Dashboard → *Zero Trust* → *Networks* → *Tunnels* → Tunnel des HomeLab → *Public Hostname* → je Host **Add a public hostname**:

| Subdomain | Domain | Service |
|---|---|---|
| `stadtfest` | `herderstreet.de` | `HTTPS` · `caddy:443` |
| `stadtfest-api` | `herderstreet.de` | `HTTPS` · `caddy:443` |
| `stadtfest-mcp` | `herderstreet.de` | `HTTPS` · `caddy:443` |
| `stadtfest-bilder` | `herderstreet.de` | `HTTPS` · `caddy:443` |

Keine Cloudflare-Access-Policy (die App, MCP-Clients und geteilte Links müssen ohne Login durchkommen). Die DNS-Einträge legt Cloudflare dabei selbst an. Der Caddy des HomeLab liefert das echte Zertifikat, „No TLS Verify“ bleibt aus.

### 3. Verzeichnisse auf dem Server

```bash
cd /volume2/docker && make bootstrap
```

oder nur die zwei Zeilen aus `scripts/bootstrap.sh` für `${APPDATA}/stadtfest` (SeaweedFS läuft als `1000:1000`).

### 4. Komodo-Variablen

Komodo → *Settings* → *Variables* → **New Variable**. Bei „Secret“ den Schalter *Secret* setzen. Die Namen müssen genau so lauten, der Stack `stadtfest` verweist mit `[[NAME]]` darauf (HomeLab `komodo/homelab/resources.toml`).

| Komodo-Variable | Secret | Wert | Woher |
|---|---|---|---|
| `STADTFEST_POSTGRES_PASSWORD` | ja | `openssl rand -hex 32` | selbst erzeugen (hex, weil es in einer URL steht) |
| `STADTFEST_NOMINATIM_DB_PASSWORD` | ja | `openssl rand -hex 32` | selbst erzeugen |
| `STADTFEST_S3_SECRET_ACCESS_KEY` | ja | `openssl rand -hex 32` | selbst erzeugen; der Stack baut daraus die SeaweedFS-Identität `stadtfest-backend` |
| `STADTFEST_SEARXNG_SECRET` | ja | `openssl rand -hex 32` | selbst erzeugen ([web-suche.md](web-suche.md)) |
| `STADTFEST_AUTH_ISSUER` | nein | `https://<instanz>.eu1.zitadel.cloud` | [zitadel.md](zitadel.md), Schritt 0 |
| `STADTFEST_ZITADEL_PROJECT_ID` | nein | Ressourcen-ID des Projekts `stadtfest` | [zitadel.md](zitadel.md), Schritt 1; wird auch für `MCP_OAUTH_SCOPES` verwendet |
| `STADTFEST_IDP_ADMIN_TOKEN` | ja | Personal Access Token | [zitadel.md](zitadel.md), Schritt 5 |
| `STADTFEST_LLM_API_KEY` | ja | Mistral-API-Schlüssel | [llm-anbieter.md](llm-anbieter.md), Schritt 2 |
| `STADTFEST_APNS_KEY_ID` | nein | Key-ID des APNs-Schlüssels | [push-apns-fcm.md](push-apns-fcm.md), Schritt 1 |
| `STADTFEST_APPLE_TEAM_ID` | nein | Apple-Team-ID | [push-apns-fcm.md](push-apns-fcm.md), Schritt 1; zugleich für Universal Links |
| `STADTFEST_APNS_KEY_BASE64` | ja | `base64 -i AuthKey_<KEYID>.p8 \| tr -d '\n'` | [push-apns-fcm.md](push-apns-fcm.md), Schritt 1 |
| `STADTFEST_FCM_PROJECT_ID` | nein | Firebase-Projekt-ID | [push-apns-fcm.md](push-apns-fcm.md), Schritt 2 |
| `STADTFEST_FCM_CREDENTIALS_BASE64` | ja | `base64 -i <dienstkonto>.json \| tr -d '\n'` | [push-apns-fcm.md](push-apns-fcm.md), Schritt 2 |
| `STADTFEST_ANDROID_CERT_SHA256` | nein | SHA-256-Fingerabdrücke, kommagetrennt; anfangs leer | [eas-build.md](eas-build.md), Schritt 3, und [store-release.md](store-release.md), Schritt 1 |
| `STADTFEST_IMPRINT_NAME` | nein | Name für das Impressum | selbst |
| `STADTFEST_IMPRINT_ADDRESS` | nein | Anschrift, Zeilen mit `\|` getrennt, z. B. `Musterweg 1\|12345 Musterstadt` | selbst |
| `STADTFEST_IMPRINT_EMAIL` | nein | Kontakt-E-Mail | selbst |

Alle anderen Werte (Anbieter, Modell, Limits, Bucket, Ports, interne Adressen, öffentliche URLs) stehen fest im HomeLab (`resources.toml` bzw. `compose.yaml`) und im Vertrag [`infra/komodo-environment.example`](../../infra/komodo-environment.example). Eine Änderung dort geht per PR.

### 5. Deployen

1. Komodo → *Stacks* → `stadtfest` → **Deploy**. Reihenfolge: Datenbanken → `stadtfest-migrate` → API, Worker, MCP → `stadtfest-edge`.
2. **Nominatim** importiert beim ersten Start Deutschland (mehrere Stunden, [nominatim.md](nominatim.md)). Bis dahin antwortet `/v1/geocode*` mit `503`, und `search_events` im MCP-Server meldet einen Tool-Fehler; alles andere läuft.
3. **Bucket anlegen** (einmalig) und die Lifecycle-Regel setzen ([objektspeicher.md](objektspeicher.md)):
   ```bash
   docker exec stadtfest-seaweedfs sh -c 'echo "s3.bucket.create -name stadtfest-images" | weed shell -master=localhost:9333'
   ```
4. Uptime Kuma (optional): HTTP-Monitor auf `https://stadtfest-api.herderstreet.de/v1/health/ready`.

### Migrationen bei laufendem Betrieb (Expand/Contract)

Beim Deploy läuft die alte API kurz gegen das neue Schema. Deshalb nur rückwärtskompatible Migrationen: erst **Expand** (neue Spalten nullable oder mit Default, neue Tabellen, alte Spalten bleiben), deployen, später **Contract** (alte Spalten entfernen, `NOT NULL`) in einem eigenen Release. So geht jeder Rollback auf den vorherigen Tag ohne Rückmigration.

## Prüfung

```bash
make smoke API_URL=https://stadtfest-api.herderstreet.de MCP_URL=https://stadtfest-mcp.herderstreet.de
```

Erwartet fünf Zeilen `ok` (Health live/ready, `GET /v1/categories`, `GET /v1/events`, MCP `search_events`; Letzteres erst nach dem Nominatim-Import). Außerdem:

- Komodo zeigt alle Container *healthy*, `stadtfest-migrate` *exited (0)*.
- `curl -sI https://stadtfest.herderstreet.de/impressum/` liefert `200`.
- Grafana zeigt Logs von `stadtfest-api` ([monitoring.md](monitoring.md)).

**Lokal geprobt (16.10.2026):** der HomeLab-Stack mit lokal gebauten Images hinter einem Caddy im Netz `edge`: Migration → API, Worker, MCP, Edge gesund; alle vier Hosts liefern die erwarteten Antworten, MCP listet seine Tools, der Objektspeicher nimmt Schreibzugriffe nur mit der erzeugten Identität an und liefert `public/` anonym aus, `pg_dump` aus `make backup` funktioniert.

## Rollback

1. Im HomeLab den Pin in `stacks/stadtfest/compose.yaml` auf den vorherigen Tag zurücksetzen (PR, oder den Renovate-Merge-Commit reverten), mergen, in Komodo *Deploy*.
2. Wegen Expand/Contract läuft der alte Code gegen das neue Schema. Eine Rückmigration (`alembic downgrade`) nur, wenn eine Migration ausnahmsweise nicht rückwärtskompatibel war, und dann vorher sichern (`make backup`, [backup-restore.md](backup-restore.md)).
3. Stack ganz anhalten: Komodo → `stadtfest` → *Stop*. Andere Stacks sind nicht betroffen.

Rollback in Produktion nach dem ersten Release einmal durchspielen und hier mit Datum eintragen.
