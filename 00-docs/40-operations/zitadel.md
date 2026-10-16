# Zitadel einrichten

## Zweck

Zitadel Cloud (EU-Region) ist in Produktion der Identity Provider der App (ADR 0003): Anmeldung per Apple, Google oder E-Mail im Hosted Login, Rollen `user`, `moderator`, `category_admin` und die Moderationsregion als Claim. Das Backend prüft die Access-Tokens über das JWKS von Zitadel und löscht Konten über die User API (ADR 0010). Eingeführt mit R05. Lokal ersetzt Keycloak Zitadel ([Lokale Entwicklung](lokale-entwicklung.md)).

## Voraussetzungen

- Zitadel-Cloud-Konto mit einer Instanz in der **EU-Region**, Rolle `IAM_OWNER` bzw. `ORG_OWNER`
- Apple Developer Account (Sign in with Apple: Services ID, Key) und Google Cloud Console (OAuth-Client)
- Zugriff auf die Komodo-Secrets der Produktion und auf die EAS-Umgebungsvariablen der App
- AV-Vertrag mit Zitadel abgeschlossen ([Auftragsverarbeiter](../30-privacy/auftragsverarbeiter.md))

## Schritte

### 1. Projekt und Rollen

1. In der Organisation ein **Projekt** `stadtfest` anlegen. Die **Projekt-ID** notieren.
2. Unter *Rollen* die Rollen `user`, `moderator` und `category_admin` anlegen (Schlüssel genau so schreiben).
3. In den Projekteinstellungen **„Assert Roles on Authentication“** und **„Check authorization on Authentication“** aktivieren. Damit steht der Claim `urn:zitadel:iam:org:project:roles` im Access-Token.
4. Neue Nutzer bekommen die Rolle `user` über die Action `add_user_role_on_registration` (nächster Abschnitt). Sie ist **Pflicht**: Wegen „Check authorization on Authentication“ kann sich ein Konto ohne Rolle im Projekt nicht anmelden. (Das Backend behandelt jeden angemeldeten Nutzer ohnehin als `user`.)

### 1a. Action `add_user_role_on_registration`

Die Action (Actions v1, JavaScript) liegt in [`infra/zitadel/actions/add_user_role_on_registration.js`](../../infra/zitadel/actions/add_user_role_on_registration.js). Sie hängt beim Anlegen eines Kontos die Rolle `user` des Projekts `stadtfest` an; liest und loggt keine personenbezogenen Daten.

1. *Organisation → Actions → Neu*:
   - **Name:** `add_user_role_on_registration` (muss genau dem Funktionsnamen im Skript entsprechen)
   - **Skript:** Inhalt der Datei einfügen und `REPLACE_WITH_PROJECT_ID` durch die Projekt-ID aus Schritt 1 ersetzen (derselbe Wert wie `AUTH_AUDIENCE`).
   - **Timeout:** 10 s
   - **Fehler zulassen („Allowed to fail“): aus** – schlägt die Action fehl, bricht die Anmeldung mit einem Fehler ab, statt ein Konto ohne Rolle zu hinterlassen.
2. *Organisation → Actions → Flows*:
   - Flow **„Internal Authentication“** (Registrierung mit E-Mail), Trigger **„Post Creation“** → Action `add_user_role_on_registration` hinzufügen.
   - Flow **„External Authentication“** (erste Anmeldung mit Apple/Google), Trigger **„Post Creation“** → dieselbe Action hinzufügen.
3. **Bestehende Konten** (vor der Action angelegt) und **in der Konsole angelegte Konten** durchlaufen die Flows nicht: Bei ihnen unter *Benutzer → Autorisierungen → Neu* das Projekt `stadtfest` mit der Rolle `user` vergeben.

> Actions v1 werden laut Zitadel mit ZITADEL v5 abgeschaltet (Datum noch offen) und bekommen keine neuen Funktionen mehr. Vor dem Upgrade auf v5 die Action durch Actions v2 ersetzen (Webhook auf das Ereignis „Benutzer angelegt“, der die Rolle über die Management-API vergibt); der Weg dahin steht im Zitadel-Leitfaden „Migrate from Actions V1 to V2“.

### 2. App-Client (Native, PKCE)

1. Im Projekt eine Anwendung vom Typ **Native** anlegen, Authentifizierung **PKCE**.
2. Redirect-URI: `stadtfest://auth`. Post-Logout-URI: `stadtfest://auth`. Für Entwicklungs-Builds mit Expo Go zusätzlich die `exp://…`-Adresse (nur in einer Test-Instanz).
3. *Token-Einstellungen:* **Auth Token Type = JWT** (sonst sind Access-Tokens opak und das Backend kann sie nicht prüfen), **Refresh Token** aktivieren.
4. Die **Client-ID** notieren.

MCP-Clients (Claude, MCP Inspector) bekommen eigene öffentliche Apps im selben Projekt: [mcp-client-anbinden.md](mcp-client-anbinden.md) (R15).

### 3. Apple und Google anbinden

1. *Organisation → Identity Providers → Neu → Apple*: Services ID, Team ID, Key ID und den privaten Schlüssel aus dem Apple Developer Account eintragen. In Apple die von Zitadel angezeigte Callback-URL als Return-URL hinterlegen.
2. *Neu → Google*: Client-ID und Secret des Google-OAuth-Clients (Typ Webanwendung) eintragen; die Callback-URL von Zitadel als autorisierte Weiterleitungs-URI in Google hinterlegen.
3. Bei beiden **„Automatic creation“** und **„Automatic update“** aktivieren, damit beim ersten Login ein Konto entsteht.
4. In der Login-Richtlinie der Organisation die beiden IdPs aktivieren sowie „Registrierung erlauben“ und „Benutzername/Passwort erlauben“.
5. Die **IdP-IDs** (in der URL der IdP-Detailseite) notieren; die App springt mit ihnen direkt zu Apple bzw. Google.

### 4. Region als Claim (entfallen)

Seit [ADR 0015](../25-adr/0015-regionen-abgeschafft.md) gibt es keine Moderationsregionen mehr. Es braucht kein Nutzer-Metadatum `region` und keine Action. Eine früher angelegte Action `setRegionClaim` im Flow „Complement Token“ kann entfernt werden; das Backend ignoriert den Claim.

### 5. Service-User für die Kontolöschung

1. *Organisation → Benutzer → Service-User → Neu*, Name `stadtfest-backend`, Token-Typ **Bearer**.
2. Unter *Organisation → Manager* den Service-User mit der Rolle **`ORG_USER_MANAGER`** hinzufügen.
3. Beim Service-User unter *Personal Access Tokens* ein Token mit Ablaufdatum (höchstens 12 Monate) erzeugen. Es wird nur einmal angezeigt. Ablaufdatum im Betriebskalender eintragen.

### 6. Secrets und Variablen hinterlegen

Backend (Komodo, **nie ins Repo**):

| Variable | Wert |
|---|---|
| `AUTH_ISSUER` | `https://<instanz>.eu1.zitadel.cloud` (ohne Schrägstrich am Ende) |
| `AUTH_AUDIENCE` | Projekt-ID aus Schritt 1 |
| `AUTH_ROLES_CLAIM` | `urn:zitadel:iam:org:project:roles` |
| `IDP_ADMIN_PROVIDER` | `zitadel` |
| `IDP_ADMIN_TOKEN` | PAT aus Schritt 5 (Secret) |

`AUTH_JWKS_URL` bleibt leer; das Backend liest den JWKS-Endpunkt aus `AUTH_ISSUER/.well-known/openid-configuration`.

App (EAS-Umgebung, zur Build-Zeit eingebettet, **nicht geheim**):

| Variable | Wert |
|---|---|
| `EXPO_PUBLIC_AUTH_ISSUER` | wie `AUTH_ISSUER` |
| `EXPO_PUBLIC_AUTH_CLIENT_ID` | Client-ID aus Schritt 2 |
| `EXPO_PUBLIC_AUTH_IDP` | `zitadel` |
| `EXPO_PUBLIC_AUTH_PROJECT_ID` | Projekt-ID aus Schritt 1 |
| `EXPO_PUBLIC_AUTH_APPLE_IDP` / `EXPO_PUBLIC_AUTH_GOOGLE_IDP` | IdP-IDs aus Schritt 3 |

### 7. Produktion vervollständigen (R16-US3)

1. **E-Mail-Absender:** *Instanz → Einstellungen → Benachrichtigungsanbieter → SMTP* mit einem EU-Mailanbieter einrichten, Absender z. B. `noreply@herderstreet.de`, Name „Stadtfest-Finder“. Für die Domain SPF, DKIM und DMARC setzen (Werte vom Mailanbieter). Ohne eigenen Absender versendet Zitadel mit seiner Standardadresse, die oft im Spam landet. Testmail über *Testen* senden.
2. **Texte und Branding:** *Organisation → Branding* Logo und Farben (Design-Tokens aus `mobile/src/theme`); *Nachrichtentexte* (Bestätigung, Passwort zurücksetzen) auf Deutsch prüfen.
3. **Links im Hosted Login:** *Organisation → Datenschutzrichtlinie*: Nutzungsbedingungen `https://stadtfest.herderstreet.de/nutzungsbedingungen/`, Datenschutz `https://stadtfest.herderstreet.de/datenschutz/`, Hilfe-/Support-E-Mail.
4. **Sicherheit:** *Login-Richtlinie* Passwort-Komplexität (mind. 10 Zeichen), Sperre nach 5 Fehlversuchen, Zwei-Faktor optional (TOTP, Passkeys). Für Admin-Konten der Instanz MFA **Pflicht**.
5. **Token-Laufzeiten** (*Instanz → OIDC-Einstellungen*): Access-Token 30 Minuten, Refresh-Token 30 Tage (gleitend). Kurze Access-Tokens verkürzen die Sperre nach einer Kontolöschung (Löschkonzept, Schritt 0).
6. **MCP-Clients:** je bekanntem Client eine eigene öffentliche App nach [mcp-client-anbinden.md](mcp-client-anbinden.md); in der Stack-Umgebung `MCP_OAUTH_SCOPES=openid profile urn:zitadel:iam:org:project:id:<projektId>:aud`.
7. **Rollen vergeben:** Moderatoren und Kategorie-Admins nach [moderator-einrichten.md](moderator-einrichten.md).
8. **Werte übernehmen:** Backend-Variablen aus Schritt 6 in die Komodo-Stack-Umgebung ([`infra/komodo-environment.example`](../../infra/komodo-environment.example)), App-Variablen in die EAS-Umgebung `production` ([eas-build.md](eas-build.md)).

**Checkliste Produktion**

- [ ] Instanz in der EU-Region, AV-Vertrag abgeschlossen
- [ ] Projekt `stadtfest` mit Rollen `user`, `moderator`, `category_admin`, „Assert Roles“ aktiv
- [ ] Action `add_user_role_on_registration` mit Projekt-ID in beiden Flows (Internal und External Authentication, Post Creation)
- [ ] Native App (PKCE, JWT-Access-Token, Refresh-Token), Redirect `stadtfest://auth`
- [ ] Apple- und Google-IdP mit automatischer Kontoerstellung
- [ ] Service-User mit `ORG_USER_MANAGER`, PAT mit Ablaufdatum im Betriebskalender
- [ ] SMTP-Absender mit SPF/DKIM, Testmail angekommen
- [ ] Datenschutz-/Nutzungsbedingungs-Links im Hosted Login
- [ ] MCP-Apps für die freigegebenen Clients

## Prüfung

1. Backend neu starten; es startet nur, wenn alle Variablen gültig sind (Fehlermeldung nennt die fehlende Variable, nie den Wert).
2. In der App „Mit E-Mail anmelden“ → Hosted Login von Zitadel erscheint → nach der Anmeldung zeigt der Drawer Name und E-Mail.
3. Ein **neues** Konto registrieren (einmal per E-Mail, einmal per Apple oder Google): In der Konsole steht beim Nutzer unter *Autorisierungen* das Projekt `stadtfest` mit der Rolle `user`, und die erste Anmeldung klappt. Fehlt die Rolle, meldet der Hosted Login „Benutzer hat keine Berechtigung“: Action-Name, Projekt-ID und Flows prüfen.
4. Mit einem Moderator anmelden: `GET /v1/me` liefert `roles: ["user", "moderator"]`. Fehlt `moderator`, sind „Assert Roles on Authentication“ oder die Projekt-Audience (`EXPO_PUBLIC_AUTH_PROJECT_ID`) nicht gesetzt.
5. „Mit Apple fortfahren“ und „Mit Google fortfahren“ springen direkt zum Anbieter.
6. Testkonto anlegen und in der App löschen: Der Nutzer ist danach in der Zitadel-Konsole nicht mehr aktiv, im Backend-Log steht kein `idp_deletion_deferred`.

### Nutzer von Hand löschen

Meldet der Worker `idp_deletion_failed`, enthält die Job-ID `delete_idp_user:<subject>` die Zitadel-Nutzer-ID. Den Nutzer in der Konsole unter *Benutzer* suchen und löschen, oder:

```bash
curl -X DELETE "$AUTH_ISSUER/v2/users/<subject>" -H "Authorization: Bearer $IDP_ADMIN_TOKEN"
```

## Rollback

- Action fehlerhaft (Anmeldungen neuer Nutzer schlagen fehl): die Action in den beiden Flows entfernen und neuen Konten die Rolle `user` von Hand geben, bis sie korrigiert ist. „Check authorization on Authentication“ **nicht** abschalten, ohne zu prüfen, dass das Backend weiter jeden Nutzer nur als `user` behandelt.
- Kompromittiertes PAT: beim Service-User löschen, neues Token erzeugen, `IDP_ADMIN_TOKEN` in Komodo ersetzen und das Backend neu starten.
- Kein Umschalten auf `IDP_ADMIN_PROVIDER=fake` in Produktion (der Start schlägt fehl); bei einem Zitadel-Ausfall bleiben Kontolöschungen im Retry-Job, bis Zitadel wieder erreichbar ist.
