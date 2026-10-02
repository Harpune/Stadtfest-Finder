# Web-Suche (SearXNG) einrichten

## Zweck

Werkzeug `web_search` des Sprachmodells in der KI-Suche (R10, Flow C). Jeder Fund braucht eine Quelle aus diesen Suchergebnissen. Die Suche läuft über ein selbst gehostetes SearXNG ([ADR 0013](../25-adr/0013-web-suche-searxng.md)): kostenlos, ohne Schlüssel, ohne neuen Auftragsverarbeiter. Optional lässt sich die Brave Search API nutzen (Abschnitt „Alternative: Brave“).

## Voraussetzungen

- Docker bzw. der Komodo-Stack auf dem eigenen Server.
- Das Image `docker.io/searxng/searxng` in der Version aus `infra/compose.dev.yaml`.
- Zugriff auf die lokale `.env` bzw. die Secrets in Komodo (Produktion).

## Schritte

### Lokal

1. SearXNG starten:
   ```bash
   docker compose -f infra/compose.dev.yaml --profile search up -d searxng
   ```
2. In `.env` setzen:
   ```bash
   WEB_SEARCH_PROVIDER=searxng
   WEB_SEARCH_BASE_URL=http://localhost:58089
   ```
3. API und Worker neu starten.

Mit `LLM_PROVIDER=fake` bringt die echte Suche nichts: Die festen Fake-Funde haben Quellen, die in keinem echten Suchergebnis stehen, und werden deshalb übersprungen. Für einen echten Lauf zusätzlich einen LLM-Anbieter einrichten ([llm-anbieter.md](llm-anbieter.md)).

### Produktion (Komodo, ab R16 in `infra/compose.yaml`)

1. **Konfiguration übernehmen:** `infra/dev/searxng/settings.yml` als Vorlage für den Server nutzen. Wichtig sind:
   - `search.formats` enthält `json`;
   - `server.limiter: false`;
   - `server.public_instance: false`.
2. **Secret erzeugen:**
   ```bash
   openssl rand -hex 32
   ```
   Den Wert als Komodo-Secret `SEARXNG_SECRET` hinterlegen. **Niemals ins Repo.**
3. **Container nur intern betreiben:** SearXNG im internen Docker-Netz des Stacks starten, **ohne** veröffentlichten Port und ohne Reverse-Proxy-Route. Nur Worker und API sprechen es an.
4. **Backend konfigurieren** (Komodo-Variablen):
   ```bash
   WEB_SEARCH_PROVIDER=searxng
   WEB_SEARCH_BASE_URL=http://searxng:8080
   ```
5. API und Worker neu deployen. Fehlt `WEB_SEARCH_BASE_URL` bei `searxng`, bricht der Start ab.

## Prüfung

- JSON-Suche direkt (lokal; in Produktion aus dem Worker-Container mit `http://searxng:8080`):
  ```bash
  curl -s "http://localhost:58089/search?q=Stadtfest%20Aalen&format=json&language=de-DE" | python3 -c 'import json,sys; b=json.load(sys.stdin); print(len(b["results"]), b["unresponsive_engines"])'
  ```
  zeigt eine Trefferzahl > 0. `403` heißt: JSON ist in `settings.yml` nicht aktiviert.
- `unresponsive_engines` listet Engines, die gerade blockieren (z. B. `CAPTCHA`, `too many requests`). Einzelne Ausfälle sind normal; fallen alle aus, enden KI-Suchen mit `search_unavailable`.
- Eine KI-Suche in der App endet mit `completed`; im Job-Protokoll (`ai_search_job.log.queries`) stehen die Suchanfragen.
- Logs: `docker logs <searxng-container>` zeigt keine `ERROR`-Zeilen beim Start. Die Warnung zur fehlenden `limiter.toml` ist harmlos, weil der Limiter aus ist.

## Störungen

- **Eine Engine blockiert dauerhaft:** in `settings.yml` unter `engines` mit `disabled: true` abschalten (wie `brave`) und den Container neu starten.
- **Engines liefern nach einem Update der Suchmaschinen nichts mehr:** Image auf eine aktuelle Version heben (Tag aus `docker image inspect … org.opencontainers.image.version`) und neu starten.

## Alternative: Brave Search API (kostenpflichtig, USA)

1. Konto auf https://api-dashboard.search.brave.com, Web-Search-Abo abschließen, DPA prüfen, Eintrag im [Verarbeiterverzeichnis](../30-privacy/auftragsverarbeiter.md) aktualisieren.
2. *API Keys → Add API key*, Name `stadtfest-prod`, dazu ein Ausgabelimit setzen.
3. `WEB_SEARCH_PROVIDER=brave` und `WEB_SEARCH_API_KEY=<subscription-token>` als Secret setzen, neu starten.
4. Prüfen ohne Ausgabe des Schlüssels:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" -H "X-Subscription-Token: $KEY" "https://api.search.brave.com/res/v1/web/search?q=Stadtfest&count=1"
   ```
   liefert `200`.

## Rollback

- **Zurück zur Fake-Suche (nur dev/test):** `WEB_SEARCH_PROVIDER=fake`.
- **KI-Suche in Produktion stoppen:** `AI_SEARCH_DAILY_LIMIT=0` setzen und neu starten.
- **SearXNG entfernen:** Container stoppen; ohne erreichbare Instanz enden Jobs mit `search_unavailable`, sonst passiert nichts.
- **Brave → SearXNG:** `WEB_SEARCH_PROVIDER=searxng` mit `WEB_SEARCH_BASE_URL` setzen, den Brave-Schlüssel im Dashboard löschen.
