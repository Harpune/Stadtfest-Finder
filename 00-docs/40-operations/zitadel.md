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
4. Unter *Organisation → Einstellungen → Standard-Rollen* bzw. per Action dafür sorgen, dass neue Nutzer die Rolle `user` bekommen. (Das Backend behandelt jeden angemeldeten Nutzer ohnehin als `user`.)

### 2. App-Client (Native, PKCE)

1. Im Projekt eine Anwendung vom Typ **Native** anlegen, Authentifizierung **PKCE**.
2. Redirect-URI: `stadtfest://auth`. Post-Logout-URI: `stadtfest://auth`. Für Entwicklungs-Builds mit Expo Go zusätzlich die `exp://…`-Adresse (nur in einer Test-Instanz).
3. *Token-Einstellungen:* **Auth Token Type = JWT** (sonst sind Access-Tokens opak und das Backend kann sie nicht prüfen), **Refresh Token** aktivieren.
4. Die **Client-ID** notieren.

### 3. Apple und Google anbinden

1. *Organisation → Identity Providers → Neu → Apple*: Services ID, Team ID, Key ID und den privaten Schlüssel aus dem Apple Developer Account eintragen. In Apple die von Zitadel angezeigte Callback-URL als Return-URL hinterlegen.
2. *Neu → Google*: Client-ID und Secret des Google-OAuth-Clients (Typ Webanwendung) eintragen; die Callback-URL von Zitadel als autorisierte Weiterleitungs-URI in Google hinterlegen.
3. Bei beiden **„Automatic creation“** und **„Automatic update“** aktivieren, damit beim ersten Login ein Konto entsteht.
4. In der Login-Richtlinie der Organisation die beiden IdPs aktivieren sowie „Registrierung erlauben“ und „Benutzername/Passwort erlauben“.
5. Die **IdP-IDs** (in der URL der IdP-Detailseite) notieren; die App springt mit ihnen direkt zu Apple bzw. Google.

### 4. Region als Claim (Action)

Die Region eines Moderators ist ein Nutzer-Metadatum `region` (z. B. `ostalb`) und muss im Access-Token als Claim `region` stehen.

1. *Actions → Neu*, Name `setRegionClaim`, Skript:

   ```javascript
   function setRegionClaim(ctx, api) {
     const metadata = ctx.v1.user.getMetadata();
     if (!metadata || !metadata.metadata) {
       return;
     }
     metadata.metadata.forEach(({key, value}) => {
       if (key === 'region' && value) {
         api.v1.claims.setClaim('region', value);
       }
     });
   }
   ```

2. *Flows → Complement Token → Trigger „Pre access token creation“* → Action `setRegionClaim` hinzufügen.
3. Wie Rolle und Region an einen Moderator vergeben werden: [Moderator einrichten](moderator-einrichten.md).

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
| `AUTH_REGION_CLAIM` | `region` |
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

## Prüfung

1. Backend neu starten; es startet nur, wenn alle Variablen gültig sind (Fehlermeldung nennt die fehlende Variable, nie den Wert).
2. In der App „Mit E-Mail anmelden“ → Hosted Login von Zitadel erscheint → nach der Anmeldung zeigt der Drawer Name und E-Mail.
3. Mit einem Moderator anmelden: `GET /v1/me` liefert `roles: ["user", "moderator"]` und `region`. Fehlt `moderator`, sind „Assert Roles on Authentication“ oder die Projekt-Audience (`EXPO_PUBLIC_AUTH_PROJECT_ID`) nicht gesetzt; fehlt `region`, läuft die Action nicht.
4. „Mit Apple fortfahren“ und „Mit Google fortfahren“ springen direkt zum Anbieter.
5. Testkonto anlegen und in der App löschen: Der Nutzer ist danach in der Zitadel-Konsole nicht mehr aktiv, im Backend-Log steht kein `idp_deletion_deferred`.

### Nutzer von Hand löschen

Meldet der Worker `idp_deletion_failed`, enthält die Job-ID `delete_idp_user:<subject>` die Zitadel-Nutzer-ID. Den Nutzer in der Konsole unter *Benutzer* suchen und löschen, oder:

```bash
curl -X DELETE "$AUTH_ISSUER/v2/users/<subject>" -H "Authorization: Bearer $IDP_ADMIN_TOKEN"
```

## Rollback

- Fehlerhafte Action: im Flow „Complement Token“ entfernen; Moderatoren verlieren dann die Moderationsrechte (das Backend loggt `moderator_without_region`), alle anderen Funktionen laufen weiter.
- Kompromittiertes PAT: beim Service-User löschen, neues Token erzeugen, `IDP_ADMIN_TOKEN` in Komodo ersetzen und das Backend neu starten.
- Kein Umschalten auf `IDP_ADMIN_PROVIDER=fake` in Produktion (der Start schlägt fehl); bei einem Zitadel-Ausfall bleiben Kontolöschungen im Retry-Job, bis Zitadel wieder erreichbar ist.
