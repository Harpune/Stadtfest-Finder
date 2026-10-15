# R15 · MCP-Server

| | |
|---|---|
| **Ziel** | Externe KI-Clients (z. B. Claude Desktop) suchen Feste und rufen Details ab. Moderatoren starten die KI-Suche. Alles läuft über dieselben Use Cases wie die REST-API. |
| **Hängt ab von** | R10 (für `start_ai_search`). Die lesenden Tools hängen nur von R02 und R05 ab und können vorgezogen werden. |
| **Quellen** | [CLAUDE.md „MCP tools“](../../CLAUDE.md), Architektur Flow D1–D3 |
| **Rollen** | öffentlich / Nutzer / Moderator |

## Umfang

**Drin:** Eigenes Paket bzw. eigener Einstiegspunkt `adapters/inbound/mcp` mit FastMCP, Streamable HTTP, OAuth gegen denselben IdP (Resource Server), drei Tools, eigenes Docker-Image `mcp`, Compose-Service.

**Nicht drin:** Weitere Tools (Favoriten, Listen). MCP folgt **nicht** der OpenAPI-Spec.

## User Stories

### R15-US1 · Server und Transport
- FastMCP-Server als eigener Prozess (`python -m stadtfest.bootstrap.mcp`) mit derselben Composition Root, Streamable HTTP unter `/mcp`.
- Health-Endpunkt für Compose und Komodo.
- **Kein Geschäftscode im Adapter:** Die Tools parsen die Eingabe, rufen den Use Case auf und mappen das Ergebnis.

### R15-US2 · Authentifizierung
- OAuth 2.1 Resource Server: Der MCP-Server veröffentlicht Protected Resource Metadata mit Zitadel (lokal Keycloak) als Authorization Server und validiert Bearer-Tokens mit derselben JWT-Logik wie die REST-API (R05, gemeinsamer Code in `adapters/inbound/auth`).
- **Ohne Token** sind nur `search_events` und `get_event` nutzbar (öffentlich, laut CLAUDE.md).
- `start_ai_search` ohne Token ergibt einen Auth-Fehler mit Hinweis auf die Anmeldung, mit Token ohne Rolle `moderator` einen Berechtigungsfehler.

### R15-US3 · Tools
| Tool | Eingabe | Use Case | Ausgabe |
|---|---|---|---|
| `search_events` | `zip_code` (5 Ziffern), `radius_km` (10–300, Standard 25), `date_from?`, `date_to?` (ISO-Datum) | Geocoding PLZ → Mittelpunkt, dann `events.search` (gleiche Sichtbarkeitsregeln wie REST). Der Zeitraum wird auf Überschneidung geprüft (entspricht `from/to`, intern zusätzlich zur Monatslogik). | Liste mit `id`, `name`, `startDate`, `endDate`, `place`, `city`, `category`, `distanceKm`, `status`, `url` (Deep Link), max. 50 Einträge |
| `get_event` | `event_id` | `events.get_public` | Detail wie `EventDetail` ohne nutzerbezogene Felder, plus `url` |
| `start_ai_search` | `zip_code` | `ai_ingestion.start_search` mit Principal | `{jobId, status}`. Dieselben Fehler wie REST (unbekannte PLZ, laufender Job, Tageslimit) als verständliche Tool-Fehler. |

- Die Tool-Beschreibungen sind deutsch/englisch und nennen die Grenzen (Deutschland, nur veröffentlichte Feste).
- **Rate-Limit** pro Token bzw. IP: 60 Aufrufe pro Minute.

### R15-US4 · Betrieb
- Eigenes Docker-Image `mcp` im CI-Build auf `main`. Service in `infra/compose.yaml` und `compose.dev.yaml`.
- Logging nach denselben Regeln: keine Tool-Eingaben wie PLZ zusammen mit Nutzer-ID, keine Tokens.

## Tests

- Unit bzw. Integration mit dem FastMCP-Testclient:
  - `search_events` und `get_event` ohne Token
  - `start_ai_search` ohne Token → Auth-Fehler, Nutzer → Berechtigungsfehler, Moderator → Job angelegt (Fake-LLM)
  - unbekannte PLZ und laufender Job
- Ein Test prüft, dass die Tools dieselben Use-Case-Funktionen aufrufen wie die REST-Router (keine Duplikation).

## Doku/Betrieb

- `40-operations/mcp-client-anbinden.md`: Claude Desktop bzw. andere Clients konfigurieren, OAuth-Client in Zitadel anlegen.
- Architektur: Flow D in `system-architecture.md`.

## Definition of Done

- [x] Rollenprüfungen für alle Tools per Test belegt (CLAUDE.md „Testing“): `backend/tests/unit/mcp/test_mcp_server.py`.
- [x] Ein manueller Test mit einem echten MCP-Client lokal ist dokumentiert: [mcp-client-anbinden.md](../40-operations/mcp-client-anbinden.md#manueller-test-lokal-15102026-r15-dod) (MCP Inspector 2.11.0, CLI und OAuth-Anmeldung im Browser).

## Offene Punkte

- ~~Unterstützt Zitadel Dynamic Client Registration für MCP-Clients?~~ **Geklärt (15.10.2026):** Zitadel kann DCR seit August 2026, aber nur mit instanzweit offener Registrierung und standardmäßig opaken Tokens (zitadel#12658). Die MCP-Spezifikation 2026-07-28 erklärt DCR für veraltet. Deshalb gibt es einen statischen OAuth-Client je bekanntem Client ([ADR 0018](../25-adr/0018-mcp-server-auth.md), [Runbook](../40-operations/mcp-client-anbinden.md)).

## Umsetzungsnotizen

- `infra/compose.yaml` gibt es erst mit R16. Der Dienst `mcp` (Image `stadtfest-mcp`, Port 8001, Health `/health/live`) kommt dort hinzu. Lokal startet `make dev` den MCP-Server wie API und Worker als Prozess, nicht als Container in `compose.dev.yaml` (dort laufen nur Abhängigkeiten).
- Zeitraum in `search_events`: neue Zeitfilter-Art `range` (Überschneidung mit `date_from`–`date_to`, offenes Ende unbegrenzt). In der App gibt es sie nicht.
- Postleitzahlen werden auch als JSON-Zahl angenommen (`1067` → `01067`), weil manche Clients Ziffern so senden.
