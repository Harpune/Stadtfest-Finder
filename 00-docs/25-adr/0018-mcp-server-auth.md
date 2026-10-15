# 0018 · MCP-Server als Ressourcenserver mit optionaler Anmeldung und statischen OAuth-Clients

- **Status:** angenommen
- **Datum:** 2026-10-15

## Kontext

R15 bringt einen MCP-Server für externe KI-Clients (Flow D). Laut CLAUDE.md sind `search_events` und `get_event` öffentlich. `start_ai_search` ist nur für Moderatoren. Die MCP-Spezifikation sieht OAuth 2.1 vor: Der Server ist Ressourcenserver und nennt in der Protected Resource Metadata (RFC 9728) seinen Authorization Server.

Zwei Probleme:

1. **FastMCP schützt den ganzen Endpunkt.** Mit einem Auth-Provider (`RemoteAuthProvider`) beantwortet FastMCP jede Anfrage ohne Token mit `401`, auch `initialize` und die öffentlichen Tools. Gäste könnten dann nicht suchen.
2. **Client-Registrierung bei Zitadel.** MCP-Clients registrieren sich üblicherweise per Dynamic Client Registration (RFC 7591). Zitadel kann das seit August 2026. Dafür müsste aber die *offene* Registrierung instanzweit eingeschaltet sein, sodass jeder OIDC-Apps in der Organisation anlegen kann. Außerdem bekommen so angelegte Apps standardmäßig opake Access-Tokens ([zitadel#12658](https://github.com/zitadel/zitadel/issues/12658), offen), die unsere JWT-Prüfung (R05) ablehnt. Die [MCP-Spezifikation 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) erklärt DCR für veraltet und empfiehlt Client ID Metadata Documents (CIMD); vorab registrierte Clients sind ausdrücklich erlaubt. Zitadel dokumentiert CIMD nicht.

## Entscheidung

1. **FastMCP ohne eigenen Auth-Provider, eigene ASGI-Middleware** (`adapters/inbound/mcp/auth.py`):
   - Ein vorhandenes Bearer-Token wird bei jeder Anfrage mit dem Use Case `Authenticate` geprüft, also mit derselben Logik wie bei der REST-API. Das Parsen des Headers liegt gemeinsam in `adapters/inbound/auth`.
   - Ein ungültiges Token ergibt `401` mit `error="invalid_token"`, auch bei öffentlichen Tools (wie REST).
   - Ohne Token sind alle Aufrufe erlaubt, außer `tools/call` für ein Tool, das eine Anmeldung braucht (`start_ai_search`). Dieser Aufruf ergibt `401` mit `resource_metadata` und `scope` im `WWW-Authenticate`-Header (RFC 6750, ohne `error`). MCP-Clients starten daraufhin die Anmeldung und wiederholen den Aufruf (Step-up).
   - Die Rollenprüfung bleibt im Use Case (`StartAiSearch` → `ForbiddenError` → Tool-Fehler „Rolle Moderator nötig“). Ein HTTP-`403` mit `insufficient_scope` passt nicht: Es fehlt eine Rolle, kein Scope, und eine neue Anmeldung würde nichts ändern.
2. **Protected Resource Metadata** unter `/.well-known/oauth-protected-resource/mcp` (und ohne Pfad): Ressource `MCP_PUBLIC_URL/mcp`, Authorization Server = `AUTH_ISSUER`, Scopes aus `MCP_OAUTH_SCOPES`.
3. **Dieselbe Audience wie die API** (`AUTH_AUDIENCE`): Zitadel setzt die Projekt-ID per Scope `urn:zitadel:iam:org:project:id:<id>:aud`, Keycloak per Audience-Mapper. Ein Token für den MCP-Server gilt damit auch für die REST-API und umgekehrt. **Bewusste Abweichung:** Die MCP-Spezifikation verlangt Tokens, die genau für den MCP-Server ausgestellt sind (RFC 8707). Zitadel bildet den `resource`-Parameter nicht auf die Audience ab. API und MCP-Server sind ein Backend mit denselben Use Cases und Rollen, aus Sicht des IdP also eine Ressource (das Projekt). Der MCP-Server reicht Tokens nie weiter (kein Token-Passthrough), ein Confused Deputy ist daher ausgeschlossen. Unterstützt der IdP später Resource Indicators, bekommt der MCP-Server eine eigene Audience (eigene Variable).
4. **Statische öffentliche OAuth-Clients** (PKCE, JWT-Access-Tokens) je bekanntem MCP-Client in Zitadel, lokal `stadtfest-mcp` in Keycloak. Die Einrichtung beschreibt [mcp-client-anbinden.md](../40-operations/mcp-client-anbinden.md).
5. **Zustandsloser Transport** (Streamable HTTP, `stateless_http`, JSON-Antworten). Jede Anfrage trägt ihr eigenes Token, der Server hält keine Sitzungen.

## Datenschutz

- Tokens werden geprüft, nicht gespeichert und nie geloggt. Das Log enthält je Tool-Aufruf nur Tool, Ergebnis und Dauer, keine PLZ und keine Nutzer-ID.
- Das Rate-Limit (60 Aufrufe/Minute) zählt je IdP-Subject bzw. IP-Adresse. Der Schlüssel wird in Redis nur als Hash gespeichert und läuft nach 60 s ab ([VVT Nr. 17](../30-privacy/verarbeitungsverzeichnis.md)).
- Der externe KI-Client und sein Anbieter (z. B. Anthropic bei Claude) sind kein Auftragsverarbeiter des Stadtfest-Finders. Der Nutzer wählt und nutzt sie selbst. Der Server liefert nur öffentliche Festdaten bzw. die Job-ID.

## Konsequenzen

- Neue Abhängigkeit `fastmcp` (≥ 4.1, mit `mcp` 2.x).
- Neuer Container `mcp` (eigenes Image `stadtfest-mcp`, Port 8001).
- Für jeden neuen MCP-Client braucht es eine App in Zitadel. Das ist gewollt: Nur bekannte Clients können sich anmelden.
- Kommen weitere Tools mit Anmeldung dazu, gehören sie in `LOGIN_TOOLS`.
- Unterstützt Zitadel später Client ID Metadata Documents oder DCR mit JWT-Tokens, lässt sich die Registrierung ohne Änderung am Server umstellen. Der Server kennt nur den Authorization Server, nicht die Clients.

## Verworfene Alternativen

- **FastMCP `RemoteAuthProvider`:** schließt Gäste aus (siehe Kontext).
- **Zwei Endpunkte** (öffentlich und angemeldet): Clients müssten zwei Server einrichten. Widerspricht der Spezifikation (ein Endpunkt `/mcp`).
- **FastMCP `OAuthProxy`** (der MCP-Server spielt Authorization Server mit DCR und leitet an Zitadel weiter): Er müsste Client-Registrierungen und Tokens selbst speichern. Das ist mehr Angriffsfläche und eigener Code für Sicherheitslogik.
- **Offene DCR in Zitadel:** instanzweit offene Registrierung und opake Tokens (siehe Kontext).
