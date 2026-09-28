# R15 · MCP-Server

| | |
|---|---|
| **Ziel** | Externe KI-Clients (z. B. Claude Desktop) suchen Feste und rufen Details ab. Moderatoren starten die KI-Suche. Alles läuft über dieselben Use Cases wie die REST-API. |
| **Hängt ab von** | R10 (für `start_ai_search`). Die lesenden Tools hängen nur von R02 und R05 ab und können vorgezogen werden. |
| **Quellen** | [CLAUDE.md „MCP tools“](../../CLAUDE.md), Architektur Flow D1–D3 |
| **Rollen** | öffentlich / Nutzer / Moderator |

## Umfang

**Drin:** Eigenes Paket bzw. eigener Einstiegspunkt `adapters/in/mcp` mit FastMCP, Streamable HTTP, OAuth gegen denselben IdP (Resource Server), drei Tools, eigenes Docker-Image `mcp`, Compose-Service.

**Nicht drin:** Weitere Tools (Favoriten, Listen). MCP folgt **nicht** der OpenAPI-Spec.

## User Stories

### R15-US1 · Server und Transport
- FastMCP-Server als eigener Prozess (`python -m stadtfest.adapters.in.mcp`) mit derselben Composition Root, Streamable HTTP unter `/mcp`.
- Health-Endpunkt für Compose und Komodo.
- **Kein Geschäftscode im Adapter:** Die Tools parsen die Eingabe, rufen den Use Case auf und mappen das Ergebnis.

### R15-US2 · Authentifizierung
- OAuth 2.1 Resource Server: Der MCP-Server veröffentlicht Protected Resource Metadata mit Zitadel (lokal Keycloak) als Authorization Server und validiert Bearer-Tokens mit derselben JWT-Logik wie die REST-API (R05, gemeinsamer Code in `adapters/in/auth`).
- **Ohne Token** sind nur `search_events` und `get_event` nutzbar (öffentlich, laut CLAUDE.md).
- `start_ai_search` ohne Token ergibt einen Auth-Fehler mit Hinweis auf die Anmeldung, mit Token ohne Rolle `moderator` einen Berechtigungsfehler.

### R15-US3 · Tools
| Tool | Eingabe | Use Case | Ausgabe |
|---|---|---|---|
| `search_events` | `zip_code` (5 Ziffern), `radius_km` (10–300, Standard 25), `date_from?`, `date_to?` (ISO-Datum) | Geocoding PLZ → Mittelpunkt, dann `events.search` (gleiche Sichtbarkeitsregeln wie REST). Der Zeitraum wird auf Überschneidung geprüft (entspricht `from/to`, intern zusätzlich zur Monatslogik). | Liste mit `id`, `name`, `startDate`, `endDate`, `place`, `city`, `category`, `distanceKm`, `status`, `url` (Deep Link), max. 50 Einträge |
| `get_event` | `event_id` | `events.get_public` | Detail wie `EventDetail` ohne nutzerbezogene Felder, plus `url` |
| `start_ai_search` | `zip_code` | `ai_ingestion.start_search` mit Principal | `{jobId, status}`. Dieselben Fehler wie REST (Region, laufender Job, Tageslimit) als verständliche Tool-Fehler. |

- Die Tool-Beschreibungen sind deutsch/englisch und nennen die Grenzen (Deutschland, nur veröffentlichte Feste).
- **Rate-Limit** pro Token bzw. IP: 60 Aufrufe pro Minute.

### R15-US4 · Betrieb
- Eigenes Docker-Image `mcp` im CI-Build auf `main`. Service in `infra/compose.yaml` und `compose.dev.yaml`.
- Logging nach denselben Regeln: keine Tool-Eingaben wie PLZ zusammen mit Nutzer-ID, keine Tokens.

## Tests

- Unit bzw. Integration mit dem FastMCP-Testclient:
  - `search_events` und `get_event` ohne Token
  - `start_ai_search` ohne Token → Auth-Fehler, Nutzer → Berechtigungsfehler, Moderator → Job angelegt (Fake-LLM)
  - fremde Region und laufender Job
- Ein Test prüft, dass die Tools dieselben Use-Case-Funktionen aufrufen wie die REST-Router (keine Duplikation).

## Doku/Betrieb

- `40-operations/mcp-client-anbinden.md`: Claude Desktop bzw. andere Clients konfigurieren, OAuth-Client in Zitadel anlegen.
- Architektur: Flow D in `system-architecture.md`.

## Definition of Done

- [ ] Rollenprüfungen für alle Tools per Test belegt (CLAUDE.md „Testing“).
- [ ] Ein manueller Test mit einem echten MCP-Client lokal ist dokumentiert.

## Offene Punkte

- Unterstützt Zitadel Dynamic Client Registration für MCP-Clients? Falls nicht: statischer OAuth-Client pro bekanntem Client, im Runbook dokumentiert.
