# Zitadel einrichten

## Zweck

Zitadel Cloud (EU-Region) ist in Produktion der Identity Provider der App (ADR 0003): Anmeldung per Apple, Google oder E-Mail im Hosted Login, Rollen `user`, `moderator` und `category_admin` als Claim. Das Backend prüft die Access-Tokens über das JWKS von Zitadel und löscht Konten über die User API (ADR 0010). Eingeführt mit R05. Lokal ersetzt Keycloak Zitadel ([Lokale Entwicklung](lokale-entwicklung.md)).

## Voraussetzungen

- Konto bei [zitadel.com](https://zitadel.com) (Schritt 0 legt die Instanz an)
- Apple-Developer-Programm (Rolle Admin) und ein Google-Konto für die [Google Cloud Console](https://console.cloud.google.com)
- Admin-Zugang zu Komodo (Variablen) und zum Expo-Projekt (EAS-Umgebungsvariablen)

### Werte, die in dieser Anleitung entstehen

| Wert | entsteht in | wird eingetragen in |
|---|---|---|
| Instanz-URL `https://<instanz>.eu1.zitadel.cloud` | Schritt 0 | Komodo-Variable `STADTFEST_AUTH_ISSUER`; EAS `EXPO_PUBLIC_AUTH_ISSUER` |
| Projekt-ID (Resource ID) | Schritt 1 | Komodo-Variable `STADTFEST_ZITADEL_PROJECT_ID` (Backend-Audience und MCP-Scope); EAS `EXPO_PUBLIC_AUTH_PROJECT_ID`; Action-Skript (Schritt 1a) |
| Client-ID der App | Schritt 2 | EAS `EXPO_PUBLIC_AUTH_CLIENT_ID` |
| IdP-ID Apple / Google | Schritt 3 | EAS `EXPO_PUBLIC_AUTH_APPLE_IDP` / `EXPO_PUBLIC_AUTH_GOOGLE_IDP` |
| Personal Access Token des Service-Users | Schritt 5 | Komodo-Variable `STADTFEST_IDP_ADMIN_TOKEN` (**secret**) |
| Client-IDs der MCP-Apps | [mcp-client-anbinden.md](mcp-client-anbinden.md) | nur im jeweiligen MCP-Client |

## Schritte

### 0. Instanz anlegen

1. Auf [zitadel.com](https://zitadel.com) registrieren, *Create Instance* → Name z. B. `stadtfest`, **Region: Europe**. Im Abrechnungsbereich den Tarif wählen und unter *Legal* den **Data Processing Agreement** akzeptieren ([Auftragsverarbeiter](../30-privacy/auftragsverarbeiter.md)).
2. Die **Instanz-URL** steht im Zitadel-Kunden-Portal bei der Instanz (*Domain*), z. B. `https://stadtfest-abc123.eu1.zitadel.cloud`. Prüfen: `curl -s https://<instanz>/.well-known/openid-configuration` liefert `"issuer": "https://<instanz>"`. Genau dieser Wert (ohne Schrägstrich am Ende) ist `STADTFEST_AUTH_ISSUER`.
3. In der Konsole der Instanz (*Console* öffnen) als Admin der Standard-Organisation arbeiten. Für das eigene Admin-Konto unter *Persönliches Profil → Multi-Faktor* einen zweiten Faktor einrichten.

### 1. Projekt und Rollen

1. In der Organisation ein **Projekt** `stadtfest` anlegen. Die **Projekt-ID** steht danach oben auf der Projektseite als *Resource Id* (nur Ziffern) → Komodo-Variable `STADTFEST_ZITADEL_PROJECT_ID`.
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
4. Die **Client-ID** wird nach dem Anlegen angezeigt (später unter der App → *Konfiguration*) → EAS-Variable `EXPO_PUBLIC_AUTH_CLIENT_ID`. Ein Client-Secret gibt es nicht (öffentlicher Client mit PKCE).

MCP-Clients (Claude, MCP Inspector) bekommen eigene öffentliche Apps im selben Projekt: [mcp-client-anbinden.md](mcp-client-anbinden.md) (R15).

### 3. Apple und Google anbinden

Die **Callback-URL** für beide Anbieter ist `https://<instanz>/idps/callback`; Zitadel zeigt sie beim Anlegen des IdP noch einmal an.

1. **Apple** (Sign in with Apple, [developer.apple.com](https://developer.apple.com/account/resources/identifiers/list)):
   1. *Identifiers* → App-ID `de.stadtfestfinder.app` öffnen (legt EAS beim ersten Build an, sonst *+ → App IDs*) → Capability **Sign in with Apple** aktivieren → speichern.
   2. *Identifiers → + → Services IDs*, Beschreibung „Stadtfest-Finder Login“, Identifier z. B. `de.stadtfestfinder.login` → anlegen → öffnen → **Sign in with Apple** aktivieren → *Configure*: Primary App ID `de.stadtfestfinder.app`, *Domains*: `<instanz>` (ohne `https://`), *Return URLs*: die Callback-URL → speichern.
   3. *Keys → +*, Name „Stadtfest-Finder Zitadel“, **Sign in with Apple** aktivieren → *Configure* → Primary App ID wählen → anlegen → `.p8` herunterladen (nur einmal möglich). Die **Key ID** steht beim Schlüssel, die **Team ID** oben rechts bzw. unter *Membership*.
   4. Zitadel: *Organisation → Identity Providers → Neu → Apple*: Client ID = Services ID (`de.stadtfestfinder.login`), Team ID, Key ID, privater Schlüssel = Inhalt der `.p8`-Datei. Scopes `name email`.
2. **Google** ([Google Cloud Console](https://console.cloud.google.com)):
   1. Projekt `stadtfest` anlegen bzw. wählen. *APIs & Services → OAuth consent screen*: User Type **External**, App-Name „Stadtfest-Finder“, Support-E-Mail, Links zu Datenschutz (`https://stadtfest.herderstreet.de/datenschutz/`) und Nutzungsbedingungen, *Authorized domains*: `zitadel.cloud` und `herderstreet.de`, Scopes `openid`, `email`, `profile`. Danach **Publish app** (sonst können sich nur Testnutzer anmelden).
   2. *Credentials → Create credentials → OAuth client ID*, Typ **Web application**, *Authorized redirect URIs*: die Callback-URL. Client-ID und Client-Secret werden angezeigt.
   3. Zitadel: *Organisation → Identity Providers → Neu → Google*: Client-ID und Client-Secret eintragen (das Secret bleibt in Zitadel, kein Komodo- oder EAS-Wert).
3. Bei beiden **„Automatic creation“** und **„Automatic update“** aktivieren, damit beim ersten Login ein Konto entsteht.
4. In der Login-Richtlinie der Organisation die beiden IdPs aktivieren sowie „Registrierung erlauben“ und „Benutzername/Passwort erlauben“.
5. Die **IdP-IDs** stehen in der Adresszeile der jeweiligen IdP-Detailseite (`…/idp/<id>`) → EAS-Variablen `EXPO_PUBLIC_AUTH_APPLE_IDP` bzw. `EXPO_PUBLIC_AUTH_GOOGLE_IDP`; die App springt mit ihnen direkt zu Apple bzw. Google.

### 4. Region als Claim (entfallen)

Seit [ADR 0015](../25-adr/0015-regionen-abgeschafft.md) gibt es keine Moderationsregionen mehr. Es braucht kein Nutzer-Metadatum `region` und keine Action. Eine früher angelegte Action `setRegionClaim` im Flow „Complement Token“ kann entfernt werden; das Backend ignoriert den Claim.

### 5. Service-User für die Kontolöschung

1. *Organisation → Benutzer → Service-User → Neu*, Name `stadtfest-backend`, Token-Typ **Bearer**.
2. Unter *Organisation → Manager* den Service-User mit der Rolle **`ORG_USER_MANAGER`** hinzufügen.
3. Beim Service-User unter *Personal Access Tokens* ein Token mit Ablaufdatum (höchstens 12 Monate) erzeugen. Es wird nur einmal angezeigt → Komodo-Variable `STADTFEST_IDP_ADMIN_TOKEN` (**secret**). Ablaufdatum im Kalender eintragen; zum Ablauf ein neues Token erzeugen, die Variable ersetzen und den Stack neu deployen.

### 6. Werte eintragen

**Backend** – Komodo → *Settings → Variables* (der HomeLab-Stack `stadtfest` setzt daraus die Backend-Variablen, [deployment-komodo.md](deployment-komodo.md), Schritt 4):

| Komodo-Variable | Secret | Wert | Backend-Variable |
|---|---|---|---|
| `STADTFEST_AUTH_ISSUER` | nein | Instanz-URL aus Schritt 0 | `AUTH_ISSUER` |
| `STADTFEST_ZITADEL_PROJECT_ID` | nein | Projekt-ID aus Schritt 1 | `AUTH_AUDIENCE`, Teil von `MCP_OAUTH_SCOPES` |
| `STADTFEST_IDP_ADMIN_TOKEN` | ja | PAT aus Schritt 5 | `IDP_ADMIN_TOKEN` |

Fest im HomeLab gesetzt (keine Eingabe nötig): `AUTH_ROLES_CLAIM=urn:zitadel:iam:org:project:roles`, `IDP_ADMIN_PROVIDER=zitadel`, `AUTH_LEEWAY_SECONDS=30`, `AUTH_TIMEOUT_SECONDS=5`. `AUTH_JWKS_URL` bleibt leer; das Backend liest den JWKS-Endpunkt aus `AUTH_ISSUER/.well-known/openid-configuration`.

**App** – EAS-Umgebungen `production` **und** `preview` ([eas-build.md](eas-build.md), Schritt 2; Sichtbarkeit *Plain text*, die Werte sind öffentlich):

| EAS-Variable | Wert |
|---|---|
| `EXPO_PUBLIC_AUTH_ISSUER` | Instanz-URL aus Schritt 0 (identisch mit `STADTFEST_AUTH_ISSUER`) |
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
6. **MCP-Clients:** je bekanntem Client eine eigene öffentliche App nach [mcp-client-anbinden.md](mcp-client-anbinden.md). `MCP_OAUTH_SCOPES` baut der HomeLab-Stack aus `STADTFEST_ZITADEL_PROJECT_ID`.
7. **Rollen vergeben:** Moderatoren und Kategorie-Admins nach [moderator-einrichten.md](moderator-einrichten.md).
8. **Werte übernehmen:** siehe Schritt 6.

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
- Kompromittiertes PAT: beim Service-User löschen, neues Token erzeugen, Komodo-Variable `STADTFEST_IDP_ADMIN_TOKEN` ersetzen und den Stack `stadtfest` neu deployen.
- Kein Umschalten auf `IDP_ADMIN_PROVIDER=fake` in Produktion (der Start schlägt fehl); bei einem Zitadel-Ausfall bleiben Kontolöschungen im Retry-Job, bis Zitadel wieder erreichbar ist.
