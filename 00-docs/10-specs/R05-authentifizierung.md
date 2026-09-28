# R05 · Authentifizierung und Konto

| | |
|---|---|
| **Ziel** | Gäste melden sich über den IdP an (Apple, Google oder E-Mail). Danach holt die App die ausgelöste Aktion nach. Das Backend validiert JWTs und kennt Rollen und Region. Nutzer können sich abmelden und ihr Konto löschen. |
| **Hängt ab von** | R04 |
| **Quellen** | [03 Authentifizierung](../15-design/workflows/03-authentifizierung.md), [Rollen und Rechte](../15-design/00-ueberblick/rollen-und-rechte.md), Screens 03-04, 03-05, 03-07. Entscheidungen E-01, E-07, E-08, E-16. |
| **Flow** | B |
| **Rollen** | Gast → Nutzer, Moderator, Kategorie-Admin |

## Umfang

**Drin:**
- App: OIDC Authorization Code + PKCE gegen Keycloak (lokal) bzw. Zitadel, sichere Token-Ablage, stilles Erneuern, Logout
- Backend: JWT-Validierung via JWKS, `GET /v1/me`, Nutzer-Anlage beim ersten Aufruf, `DELETE /v1/me` (Konto löschen)
- UI: Einstieg-Screen, Gast-Drawer (03-07), minimaler angemeldeter Drawer mit Abmelden und Konto-Seite, Ausführen von `pendingAction`

**Nicht drin:**
- Zeitleiste im Drawer (R06)
- Push-Token-Registrierung (R11)
- Eigene Endpunkte `/auth/*`: Sie **entfallen** (E-01).

## User Stories

### R05-US1 · Einstieg „Anmelden oder registrieren“
Ersetzt die Formular-Screens 03-04 bis 03-06.

- Vollbild von unten (380 ms) mit Titel „Willkommen“ und „Favoriten, Einladungen und Erinnerungen an einem Ort.“
- Buttons:
  - „Mit Apple fortfahren“ (nur iOS verpflichtend, auf Android optional)
  - „Mit Google fortfahren“
  - „Mit E-Mail anmelden“
  - „Konto erstellen“
- Jeder Button startet den Authorization-Code-Flow mit PKCE im System-Browser-Sheet (`expo-auth-session`):
  - Apple/Google mit IdP-Hinweis, sodass der Hosted Login direkt zum jeweiligen Anbieter springt
  - „Konto erstellen“ mit `prompt=create`
- Rechtshinweis unten (Nutzungsbedingungen, Datenschutz) als Links.
- Passwort vergessen, E-Mail-Bestätigung und Validierungsfehler laufen vollständig im Hosted Login.
- **Abbruch** im Browser: zurück zum Einstieg, kein Fehler-Toast. **Fehler** (Netz, IdP): Toast „Anmeldung fehlgeschlagen · Bitte erneut versuchen“.

### R05-US2 · Nach der Anmeldung
- Tokens werden in `expo-secure-store` (Keychain/Keystore) gespeichert, nie in AsyncStorage.
- Die App ruft `GET /v1/me` auf und hält das Profil im Auth-Store.
- `pendingAction` wird ausgeführt:
  - `favorite`: ab R06 Favorit setzen + Toast „Angemeldet · Fest gemerkt“
  - `share` / `invite`: die Aktion erneut öffnen
  - ohne Aktion: Toast „Willkommen, {Vorname}!“
- Liefert der IdP keinen Vornamen (Apple ohne Namensfreigabe), fragt ein Sheet beim ersten Öffnen des Drawers nach Vor- und Nachnamen. Das speichert `PATCH /v1/me {firstName, lastName}`.

### R05-US3 · Backend: JWT und `/me`
- Middleware bzw. Dependency validiert Bearer-Tokens:
  - Signatur über JWKS (gecacht, Rotation durch Neuladen bei unbekannter `kid`)
  - `iss`, `aud`, `exp`, `nbf`, Algorithmus RS256/ES256
- Rollen- und Region-Claim sind per Settings konfigurierbar (`AUTH_ROLES_CLAIM`, `AUTH_REGION_CLAIM`), damit Keycloak und Zitadel mit derselben Codebasis laufen. Mapping in einen Domain-`Principal {userId, roles, regionKey}`.
- Öffentliche Endpunkte akzeptieren **optional** ein Token. Ein ungültiges Token ergibt dort ebenfalls `401` (der Client erneuert es).
- `GET /v1/me` → `{id, firstName, lastName, roles[], region: {id, key, name}?}`:
  - Beim ersten Aufruf wird der Nutzer angelegt (Upsert auf `sub`). Vor- und Nachname kommen aus den Claims `given_name` / `family_name`.
  - **Die E-Mail wird nicht gespeichert** (E-08). Die App liest sie aus dem ID-Token.
- `PATCH /v1/me {firstName, lastName}`: je 1–50 Zeichen, getrimmt.
- Hat ein Token die Rolle `moderator`, aber keine gültige Region, fehlen dem Principal die Moderationsrechte, und es wird eine Warnung ohne Nutzerdaten geloggt.

### R05-US4 · Token erneuern und abmelden
- **Access-Token abgelaufen:** Die App erneuert es still mit dem Refresh-Token (ein zentraler Interceptor, parallele Requests warten auf eine Erneuerung).
- **Erneuern schlägt fehl:** Rückfall in den Gastmodus, Toast „Bitte melde dich erneut an“.
- **„Abmelden“ im Drawer:**
  - Refresh-Token beim IdP widerrufen (Revocation-Endpoint), lokale Tokens löschen
  - Seitenstapel schließen, Query-Cache nutzerbezogener Daten leeren
  - Toast „Du bist abgemeldet“
  - Ab R11 wird vorher `DELETE /v1/me/devices/{token}` aufgerufen.

### R05-US5 · Drawer (Grundgerüst)
- Das Profilbild oben rechts zeigt als Gast ein Gast-Icon, angemeldet die Initialen.
- **Gast-Drawer (03-07):** „Deine Festsaison auf einen Blick“, Nutzen-Text, angedeutete Zeitleiste (Skeleton, Deckkraft .5), Login-Button, „Alle Feste kannst du auch ohne Konto entdecken.“
- **Angemeldeter Drawer:** Nutzerzeile (Avatar 32, Name, E-Mail aus dem ID-Token, ✕), Fußbereich mit „Abmelden“. Die Zeitleiste folgt in R06.
- Ein Tipp auf die Nutzerzeile öffnet die Seite **„Konto“**: Name ändern, „Konto löschen“.

### R05-US6 · Konto löschen (Art. 17 DSGVO, App-Store-Pflicht)
- Auf der Konto-Seite: „Konto löschen“ (Rosa) → Dialog „Konto endgültig löschen?“ mit Erklärung, was gelöscht wird, und „Endgültig löschen“.
- `DELETE /v1/me` → `204`. Der Use Case `DeleteAccount`:
  1. löscht alle personenbezogenen Daten des Nutzers im Backend in einer Transaktion. Jedes spätere Inkrement erweitert diese Liste (siehe README, Regel 7).
  2. löscht den Nutzer beim IdP über den **IdP-Admin-Port** (Zitadel Management API mit Service-User; lokal Keycloak Admin API; in Tests ein Fake).
  3. setzt Audit-Felder (`createdBy`, `updatedBy`) auf `null`, wenn der Nutzer Moderator war.
- Schlägt Schritt 2 fehl, landet ein Retry-Job in der Queue. Die lokalen Daten sind dann bereits gelöscht.
- Die App meldet danach lokal ab, Toast „Dein Konto wurde gelöscht“.

## Autorisierung (gilt ab jetzt für alle Inkremente)

| Situation | Ergebnis |
|---|---|
| Kein oder ungültiges Token an einem geschützten Endpunkt | `401` → Client erneuert das Token, sonst Gast-Hinweis |
| Rolle fehlt (`/v1/mod/*`) | `403` → Client schließt die Moderationsansicht, Toast |
| Fest einer fremden Region | `404` |

Die Prüfungen liegen in den Use Cases (`Principal` wird übergeben), nicht in den Routern.

## Daten

`app_user`: `id` (uuid, intern), `idp_subject` (unique), `first_name`, `last_name`, `created_at`, `updated_at`. **Keine** E-Mail und keine Provider-Liste.

## Datenschutz

- VVT-Eintrag „Nutzerkonto“: Zweck, Daten (IdP-Subject, Name), Rechtsgrundlage Art. 6 (1) b, Löschung sofort bei Kontolöschung.
- Löschkonzept: Ablauf `DeleteAccount` inkl. IdP-Löschung und Retry.
- Tokens werden nie geloggt (Test aus R01 um `Authorization` erweitert).

## Tests

- Unit: `DeleteAccount` mit Fake-Ports (lokale Daten weg, IdP-Aufruf, Retry bei Fehler), Claim-Mapping (Keycloak- und Zitadel-Format), Principal ohne Region.
- Integration:
  - JWT-Validierung gegen einen lokal signierten JWKS: abgelaufen, falsches `aud`, fremder Schlüssel, `kid`-Rotation
  - Keycloak-Testcontainer für einen echten Login-Roundtrip (ein Test)
- Contract: `/v1/me` (`401` ohne Token).
- Mobile: Interceptor (paralleles Refresh), Ausführen von `pendingAction`, Rückfall in den Gastmodus.
- Maestro `login.yaml`: Gast → Herz → Gast-Hinweis → Anmelden (Keycloak-Testnutzer im Browser) → zurück in der App → Drawer zeigt den Namen → Abmelden.

## Doku/Betrieb

- `40-operations/zitadel.md`:
  - Projekt, App-Client (PKCE, Redirect-URIs), Rollen
  - Apple- und Google-IdP anbinden
  - Region-Metadatum und Claim (Action)
  - Service-User für Kontolöschung
- `40-operations/moderator-einrichten.md`: Rolle und Region vergeben (E-07).
- ADR: IdP-Admin-Port für die Kontolöschung.

## Definition of Done

- [ ] Login, Logout und Konto löschen funktionieren lokal gegen Keycloak auf iOS und Android.
- [ ] Die Moderationsrolle wird korrekt erkannt (Testnutzer `moderator`).
- [ ] Der Maestro-Flow „Login“ ist grün.
- [ ] VVT und Löschkonzept sind aktualisiert.

## Offene Punkte

- Muss die E-Mail vor der ersten Account-Aktion bestätigt sein? Vorschlag: nein.
- Gestaltung der Konto-Seite und des Einstiegs-Screens: Designlücke, im Stil der bestehenden Screens umsetzen und nachträglich ins Design übernehmen.
