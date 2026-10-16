# MCP-Client anbinden

## Zweck

Externe KI-Clients (Claude Code, Claude Desktop bzw. claude.ai, MCP Inspector) greifen über den MCP-Server auf den Stadtfest-Finder zu (Flow D, [R15](../10-specs/R15-mcp-server.md), [ADR 0018](../25-adr/0018-mcp-server-auth.md)). `search_events` und `get_event` funktionieren ohne Anmeldung. `start_ai_search` braucht eine Anmeldung mit der Rolle `moderator`.

Der MCP-Server ist ein OAuth-2.1-Ressourcenserver. Er veröffentlicht unter `/.well-known/oauth-protected-resource/mcp` Zitadel (lokal Keycloak) als Authorization Server. Ein Client ohne Token bekommt beim Aufruf von `start_ai_search` die Antwort `401` mit `resource_metadata`. Daraufhin startet der Client die Anmeldung (Authorization Code + PKCE) und wiederholt den Aufruf.

**Keine Dynamic Client Registration (DCR):** Zitadel kann DCR seit August 2026. Für MCP-Clients müsste aber die *offene* Registrierung instanzweit an sein, sodass jeder OIDC-Apps anlegen könnte. Außerdem bekommen so registrierte Apps standardmäßig opake Access-Tokens ([zitadel#12658](https://github.com/zitadel/zitadel/issues/12658), Stand 09.10.2026 offen), die das Backend nicht prüfen kann. Deshalb gibt es je bekanntem Client eine **statische, öffentliche OAuth-App** mit PKCE. Der Client bekommt ihre Client-ID von Hand.

## Voraussetzungen

- Zitadel eingerichtet nach [zitadel.md](zitadel.md): Projekt `stadtfest` mit Rollen und „Assert Roles on Authentication“. Die Projekt-ID ist bekannt.
- Rolle *Project Owner* (oder höher) in Zitadel
- MCP-Server öffentlich per HTTPS erreichbar, in Produktion `https://stadtfest-mcp.herderstreet.de/mcp` (Cloudflare Tunnel → HomeLab-Caddy → `stadtfest-edge`, [deployment-komodo.md](deployment-komodo.md)). Claude Desktop und claude.ai verbinden sich **aus der Anthropic-Cloud**, nicht vom eigenen Rechner. Ein lokaler Server ist für sie also nicht erreichbar. Claude Code und der MCP Inspector laufen lokal.
- Lokal: Stack aus [lokale-entwicklung.md](lokale-entwicklung.md), Node.js für den MCP Inspector

## Schritte

### 1. OAuth-Apps in Zitadel anlegen (eine je Client)

Im Projekt `stadtfest` für jeden Client eine Anwendung anlegen:

| App | Typ | Authentifizierung | Redirect-URI |
|---|---|---|---|
| `mcp-claude` (Claude Desktop, claude.ai) | Web | PKCE | `https://claude.ai/api/mcp/auth_callback` |
| `mcp-claude-code` | Native | PKCE | `http://localhost:33418/callback` (fester Port, siehe Schritt 3) |
| `mcp-inspector` (nur Test-Instanz) | Web | PKCE | `http://localhost:6274/oauth/callback` |

Für jede App:

1. *Token-Einstellungen:* **Auth Token Type = JWT**. Ohne diese Einstellung sind die Access-Tokens opak und der MCP-Server lehnt sie ab (`401 invalid_token`).
2. `http://`-Redirects (Claude Code, Inspector) erlauben nur Apps im **Development Mode**. Für Loopback-Adressen ist das nach RFC 8252 vorgesehen. Für `mcp-claude` bleibt er aus.
3. **Client-ID** notieren. Es gibt kein Client-Secret (öffentlicher Client).

### 2. MCP-Server konfigurieren

In Produktion ist nichts einzutragen: Der HomeLab-Stack `stadtfest` setzt die Werte selbst.

| Variable | Wert in Produktion | Quelle |
|---|---|---|
| `MCP_PUBLIC_URL` | `https://stadtfest-mcp.herderstreet.de` (ohne `/mcp`) | HomeLab-Compose-Datei aus `DOMAIN` |
| `MCP_OAUTH_SCOPES` | `openid profile urn:zitadel:iam:org:project:id:<Projekt-ID>:aud` | HomeLab `resources.toml` mit der Komodo-Variable `STADTFEST_ZITADEL_PROJECT_ID` |
| `DEEP_LINK_BASE_URL` | `https://stadtfest.herderstreet.de` | HomeLab-Compose-Datei aus `DOMAIN` |
| `AUTH_ISSUER`, `AUTH_AUDIENCE`, `AUTH_ROLES_CLAIM` | wie bei der API | [zitadel.md](zitadel.md), Schritt 6 |

Lokal stehen die Werte in `.env` (siehe `.env.example`). Der Audience-Scope sorgt dafür, dass die Projekt-ID (= `AUTH_AUDIENCE`) im Token steht. Die Clients fordern die Scopes aus der Protected Resource Metadata an. Die **Client-IDs** aus Schritt 1 sind keine Server-Variablen; sie werden nur im jeweiligen Client eingetragen (Schritt 3). Der Container ist `stadtfest-mcp` (Image `ghcr.io/harpune/stadtfest-mcp`, Port 8001, Health `/health/live` und `/health/ready`).

### 3. Clients einrichten

- **Claude Code:**

  ```bash
  claude mcp add --transport http --client-id <Client-ID mcp-claude-code> --callback-port 33418 stadtfest https://stadtfest-mcp.herderstreet.de/mcp
  ```

  Danach in Claude Code `/mcp` → `stadtfest` → *Authenticate*.
- **Claude Desktop / claude.ai:** *Einstellungen → Konnektoren → Benutzerdefinierten Konnektor hinzufügen*. URL `https://stadtfest-mcp.herderstreet.de/mcp` eintragen, unter *Erweiterte Einstellungen* die **OAuth Client ID** von `mcp-claude`. Das Client-Secret bleibt leer.
- **MCP Inspector** (`npx @modelcontextprotocol/inspector`): Server mit Transport *Streamable HTTP* anlegen, unter *Settings → OAuth Settings* die Client-ID eintragen, Scopes wie `MCP_OAUTH_SCOPES`.

### Lokal (Keycloak)

Der Dev-Realm enthält den öffentlichen Client **`stadtfest-mcp`** (PKCE, Audience `stadtfest-api`). Er erlaubt diese Redirects:

- `http://localhost:*` und `http://127.0.0.1:*` (beliebiger Port)
- `http://localhost:6274/oauth/callback` (Inspector)
- `https://claude.ai/api/mcp/auth_callback`

`make dev` startet den MCP-Server unter `http://localhost:8001/mcp`, `make mcp` startet ihn allein. Eine schon laufende Keycloak-Instanz importiert den Realm nicht erneut. Neu erzeugen mit:

```bash
docker compose -f infra/compose.dev.yaml up -d --force-recreate keycloak
```

Dabei gehen lokal registrierte Konten verloren, die Testnutzer aus dem Realm bleiben.

## Prüfung

1. Metadaten:

   ```bash
   curl -s https://stadtfest-mcp.herderstreet.de/.well-known/oauth-protected-resource/mcp
   ```

   Erwartet: `resource` = `…/mcp`, `authorization_servers` = Zitadel-Issuer, `scopes_supported` wie `MCP_OAUTH_SCOPES`.
2. Ohne Anmeldung: Im Client „Feste um 73430“ fragen bzw. `search_events` aufrufen → Liste mit Links `https://stadtfest.herderstreet.de/f/<id>`.
3. `start_ai_search` ohne Anmeldung → Der Client öffnet die Zitadel-Anmeldung. Danach gilt:
   - Mit Nutzerkonto: Tool-Fehler „Dafür fehlt dir die Rolle Moderator“.
   - Mit Moderatorkonto: `{jobId, status: "queued"}`, der Auftrag erscheint in der App unter „KI-Suche“.
4. Im Log des Containers stehen je Aufruf nur `mcp_tool_call` mit Tool, Ergebnis und Dauer. Es gibt keine PLZ, keine Nutzer-ID und keine Tokens.

### Manueller Test lokal (15.10.2026, R15-DoD)

Lokaler Stack mit Seed-Daten, MCP-Server aus diesem Branch. Client war der **MCP Inspector 2.11.0** (offizieller Referenz-Client, Protokoll 2025-11-25).

| Schritt | Client / Konto | Ergebnis |
|---|---|---|
| `tools/list` | CLI, ohne Token | 3 Tools mit deutsch/englischen Beschreibungen |
| `search_events` 73430, 50 km | CLI, ohne Token | 23 Feste, z. B. „Reichsstädter Tage“, Kategorie, Entfernung 0,1 km, Deep Link |
| `get_event` | CLI, ohne Token | Detail mit 4 Programmpunkten, ohne `isFavorite` |
| `start_ai_search` | CLI, ohne Token | HTTP `401`, `WWW-Authenticate: Bearer resource_metadata="…/.well-known/oauth-protected-resource/mcp", scope="openid profile"`. Der Inspector startet daraufhin die OAuth-Anmeldung. |
| `start_ai_search` | CLI, Token `nutzer@example.test` | Tool-Fehler „Dafür fehlt dir die Rolle Moderator.“ |
| `start_ai_search` 99999 | CLI, Token `moderator@example.test` | Rolle geprüft, Tool-Fehler „Diese Postleitzahl kennen wir nicht.“ (kein Auftrag angelegt) |
| beliebiger Aufruf | CLI, ungültiges Token | HTTP `401` mit `error="invalid_token"` |
| `start_ai_search` 99999 | **Web-Oberfläche mit OAuth**, Client-ID `stadtfest-mcp` | `401` → Metadaten → Keycloak-Anmeldung (PKCE, `resource=http://localhost:8012/mcp`) → als `moderator@example.test` angemeldet → Aufruf mit Token, Tool-Fehler „Diese Postleitzahl kennen wir nicht.“ |

Gefunden und behoben: Der Inspector schickt Ziffern als JSON-Zahl (`zip_code: 73430`). Der Server nimmt Postleitzahlen deshalb auch als Zahl an und füllt sie auf fünf Stellen auf.

Nachstellen (CLI, Tokens per Password-Grant des Dev-Clients `stadtfest-tests`):

```bash
npx -y @modelcontextprotocol/inspector@2.11.0 --cli http://localhost:8001/mcp --transport http --method tools/call --tool-name search_events --tool-arg zip_code=73430 --tool-arg radius_km=50
```

## Rollback

- Einzelnen Client sperren: die App in Zitadel deaktivieren oder löschen. Ausgestellte Tokens laufen mit ihrer Lebensdauer ab.
- MCP-Zugang ganz abschalten: `docker stop stadtfest-mcp` (bis zum nächsten Deploy) bzw. den Dienst im HomeLab-Stack entfernen. API und Worker sind unabhängig davon.
- Nur die KI-Suche stoppen: `AI_SEARCH_DAILY_LIMIT=0` im HomeLab `resources.toml` (gilt für REST und MCP).
