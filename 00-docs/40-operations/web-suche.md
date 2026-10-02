# Web-Suche (Brave Search API) einrichten

## Zweck

Werkzeug `web_search` des Sprachmodells in der KI-Suche (R10, Flow C). Jeder Fund braucht eine Quelle aus diesen Suchergebnissen. Anbieter ist die Brave Search API ([ADR 0013](../25-adr/0013-web-suche-brave.md)), nach außen gehen nur Suchanfragen ohne Personenbezug.

## Voraussetzungen

- Ein Konto auf https://api-dashboard.search.brave.com mit hinterlegter Zahlungsart (auch der kostenlose Tarif verlangt sie).
- Zugriff auf die lokale `.env` bzw. die Secrets in Komodo (Produktion).

## Schritte

1. **Tarif wählen:** Im Dashboard unter *Plans* einen Tarif für die **Web Search** abonnieren. Die Nutzung ist gering: höchstens `AI_SEARCH_MAX_TOOL_CALLS` Anfragen (Standard 8) je KI-Suche, höchstens `AI_SEARCH_DAILY_LIMIT` Suchen (Standard 10) je Moderator und Tag. Aktuelle Preise und Limits (Anfragen pro Sekunde und Monat) stehen im Dashboard.
2. **Datenschutz:** Die Nutzungsbedingungen und das Data Processing Addendum von Brave prüfen und den Status im [Verarbeiterverzeichnis](../30-privacy/auftragsverarbeiter.md) eintragen.
3. **Schlüssel anlegen:** *API Keys → Add API key*, Name `stadtfest-prod` (für Entwicklung `stadtfest-dev`), dem Web-Search-Abo zuordnen.
4. **Ausgabegrenze setzen**, falls der Tarif nutzungsabhängig abrechnet (*Usage limits*).
5. **Secrets hinterlegen** – lokal in `.env` (siehe `.env.example`), in Produktion als Komodo-Secret. **Niemals ins Repo.**
   ```bash
   WEB_SEARCH_PROVIDER=brave
   WEB_SEARCH_API_KEY=<subscription-token>
   ```
6. **API und Worker neu starten.** Fehlt der Schlüssel bei `brave`, bricht der Start ab.

## Prüfung

- Schlüssel testen, ohne ihn auszugeben (`$KEY` vorher aus dem Passwort-Manager in die Shell laden):
  ```bash
  curl -s -o /dev/null -w "%{http_code}\n" -H "X-Subscription-Token: $KEY" "https://api.search.brave.com/res/v1/web/search?q=Stadtfest%20Aalen&count=1"
  ```
  liefert `200`. `401`/`403` heißt Schlüssel falsch oder kein Abo, `429` Limit erreicht.
- Eine KI-Suche in der App endet mit `completed`; im Job-Protokoll (`ai_search_job.log.queries`) stehen die Suchanfragen.
- Im Brave-Dashboard (*Usage*) erscheinen die Anfragen.

## Rollback

- **Suche ausfallen lassen:** Ohne gültigen Schlüssel enden Jobs mit `search_unavailable`; es werden keine Entwürfe angelegt, sonst passiert nichts.
- **KI-Suche ganz stoppen:** `AI_SEARCH_DAILY_LIMIT=0` setzen und neu starten.
- **Schlüssel kompromittiert:** im Dashboard löschen, neuen anlegen, Secret ersetzen, neu starten.
- **Anbieter wechseln:** neuer Adapter für `WebSearchPort` plus ADR, dann `WEB_SEARCH_PROVIDER` umstellen.
- In Entwicklung und Tests: `WEB_SEARCH_PROVIDER=fake`.
