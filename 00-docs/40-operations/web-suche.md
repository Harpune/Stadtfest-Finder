# Web-Suche (SearXNG) einrichten

## Zweck

Werkzeug `web_search` des Sprachmodells in der KI-Suche (R10, Flow C). Jeder Fund braucht eine Quelle aus diesen Suchergebnissen. Die Suche läuft über ein selbst gehostetes SearXNG ([ADR 0013](../25-adr/0013-web-suche-searxng.md)): kostenlos, ohne Schlüssel, ohne neuen Auftragsverarbeiter. Optional lässt sich die Brave Search API nutzen (Abschnitt „Alternative: Brave“).

## Voraussetzungen

- Docker bzw. der Komodo-Stack auf dem eigenen Server.
- Das Image `docker.io/searxng/searxng` in der Version aus `infra/compose.dev.yaml` (lokal) bzw. `infra/searxng/Dockerfile` (Produktion).
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

### Produktion (HomeLab-Stack `stadtfest`)

1. **Image:** `ghcr.io/harpune/stadtfest-searxng` (aus `infra/searxng/`, Einstellungen fest eingebaut: JSON-Ausgabe an, Limiter aus, keine öffentliche Instanz, keine Metriken). Der Container `stadtfest-searxng` läuft nur im internen Netz, ohne Port und ohne Route.
2. **Secret:** `openssl rand -hex 32` → Komodo-Variable `STADTFEST_SEARXNG_SECRET` (*Secret*, [deployment-komodo.md](deployment-komodo.md), Schritt 4). **Niemals ins Repo.**
3. **Backend:** `WEB_SEARCH_PROVIDER=searxng` steht fest im Stack, `WEB_SEARCH_BASE_URL=http://stadtfest-searxng:8080` setzt die HomeLab-Compose-Datei. Keine weitere Eingabe.
4. Engines ändern: `infra/searxng/settings.yml` anpassen, neuen Release taggen, Renovate-PR im HomeLab mergen, deployen.

## Prüfung

- JSON-Suche direkt (lokal; in Produktion `docker exec stadtfest-searxng wget -q -O - "http://127.0.0.1:8080/search?q=Stadtfest&format=json"`):
  ```bash
  curl -s "http://localhost:58089/search?q=Stadtfest%20Aalen&format=json&language=de-DE" | python3 -c 'import json,sys; b=json.load(sys.stdin); print(len(b["results"]), b["unresponsive_engines"])'
  ```
  zeigt eine Trefferzahl > 0. `403` heißt: JSON ist in `settings.yml` nicht aktiviert.
- `unresponsive_engines` listet Engines, die gerade blockieren (z. B. `CAPTCHA`, `too many requests`). Einzelne Ausfälle sind normal; fallen alle aus, enden KI-Suchen mit `search_unavailable`.
- Eine KI-Suche in der App endet mit `completed`; im Job-Protokoll (`ai_search_job.log.queries`) stehen die Suchanfragen.
- Logs: `docker logs stadtfest-searxng` zeigt keine `ERROR`-Zeilen beim Start. Die Warnung zur fehlenden `limiter.toml` ist harmlos, weil der Limiter aus ist.

## Störungen

- **Wenige Engines aktiv:** Ab Werk sind für die allgemeine Websuche nur DuckDuckGo und Google CSE aktiv; beide blockierten bei Tests nach etwa 60 Anfragen pro Stunde. `infra/dev/searxng/settings.yml` aktiviert zusätzlich Bing, Google, Qwant, Yahoo und GMX. Welche Engines gerade blockieren, zeigt `unresponsive_engines` in der JSON-Antwort.

- **Eine Engine blockiert dauerhaft:** in `infra/searxng/settings.yml` (Produktion) bzw. `infra/dev/searxng/settings.yml` (lokal) unter `engines` mit `disabled: true` abschalten (wie `brave`); lokal den Container neu starten, in Produktion neuen Release bauen und deployen.
- **Engines liefern nach einem Update der Suchmaschinen nichts mehr:** Image auf eine aktuelle Version heben (Tag aus `docker image inspect … org.opencontainers.image.version`) und neu starten.

## Alternative: Brave Search API (kostenpflichtig, USA)

1. Konto auf https://api-dashboard.search.brave.com, Web-Search-Abo abschließen, DPA prüfen, Eintrag im [Verarbeiterverzeichnis](../30-privacy/auftragsverarbeiter.md) aktualisieren.
2. *API Keys → Add API key*, Name `stadtfest-prod`, dazu ein Ausgabelimit setzen.
3. Lokal `WEB_SEARCH_PROVIDER=brave` und `WEB_SEARCH_API_KEY=<subscription-token>` in `.env`. Produktion: Komodo-Variable `STADTFEST_WEB_SEARCH_API_KEY` (*Secret*) anlegen und im HomeLab (`komodo/homelab/resources.toml`, Stack `stadtfest`) `WEB_SEARCH_PROVIDER=brave` und `WEB_SEARCH_API_KEY=[[STADTFEST_WEB_SEARCH_API_KEY]]` setzen (PR), dann deployen.
4. Prüfen ohne Ausgabe des Schlüssels:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" -H "X-Subscription-Token: $KEY" "https://api.search.brave.com/res/v1/web/search?q=Stadtfest&count=1"
   ```
   liefert `200`.

## Rollback

- **Zurück zur Fake-Suche (nur dev/test):** `WEB_SEARCH_PROVIDER=fake`.
- **KI-Suche in Produktion stoppen:** im HomeLab (`komodo/homelab/resources.toml`, Stack `stadtfest`) `AI_SEARCH_DAILY_LIMIT=0` setzen (PR) und deployen.
- **SearXNG anhalten:** `docker stop stadtfest-searxng`; ohne erreichbare Instanz enden Jobs mit `search_unavailable`, sonst passiert nichts.
- **Brave → SearXNG:** `WEB_SEARCH_PROVIDER=searxng` mit `WEB_SEARCH_BASE_URL` setzen, den Brave-Schlüssel im Dashboard löschen.
