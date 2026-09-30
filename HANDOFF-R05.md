# Handoff R05 · Authentifizierung und Konto

> Arbeitsnotiz für die lokale Weiterarbeit an PR #9. **Vor dem Merge löschen** (gehört nicht nach `main`).

| | |
|---|---|
| **PR** | https://github.com/Harpune/Stadtfest-Finder/pull/9 |
| **Branch** | `feature/r05-authentifizierung-fxvo2z` (Basis `main` @ `e5b39be`) |
| **Spec** | [`00-docs/10-specs/R05-authentifizierung.md`](00-docs/10-specs/R05-authentifizierung.md) |
| **CI** | alle Checks grün (Backend, Mobile, OpenAPI, Codegen-Drift, Trivy, CodeQL, AI-Review), keine Review-Kommentare |
| **Stand** | Code und Doku fertig; **Prüfung auf Gerät/Simulator fehlt** (DoD) |

## 1. Lokal loslegen

```bash
git fetch origin
git switch feature/r05-authentifizierung-fxvo2z
git pull

# Neue Variablen übernehmen (Backend: AUTH_*, IDP_ADMIN_*; App: EXPO_PUBLIC_AUTH_*)
diff .env .env.example
diff mobile/.env mobile/.env.example

# Keycloak neu anlegen: importiert den Realm sonst nicht neu (neuer Client stadtfest-admin)
docker compose -f infra/compose.dev.yaml up -d --force-recreate keycloak

make install        # PyJWT, expo-auth-session, expo-crypto, expo-secure-store
make dev            # führt auch Migration 0003 (app_user) aus
make seed

# Neue native Module → neuer Development-Build nötig
cd mobile && pnpm ios   # bzw. pnpm android
```

**Android-Emulator:** `adb reverse tcp:58080 tcp:58080 && adb reverse tcp:8000 tcp:8000`. Sonst stimmt `localhost` nicht, und der Issuer im Token passt nicht zum Backend.

**Testnutzer** (Passwort `stadtfest-dev`): `nutzer@example.test`, `moderator@example.test` (Region `ostalb`), `katadmin@example.test`.

## 2. Was noch zu tun ist

### Muss vor dem Merge passieren (Definition of Done R05)

- [ ] **Login, Logout und Konto löschen auf iOS** gegen Keycloak durchspielen.
  - Gast → Herz → Gast-Hinweis → „Anmelden oder registrieren“ → „Mit E-Mail anmelden“ → Keycloak-Login → zurück in der App mit Toast „Angemeldet · Fest gemerkt“.
  - Drawer zeigt Initialen, Name und E-Mail. „Abmelden“ zeigt „Du bist abgemeldet“.
  - Konto-Seite: Name ändern, dann „Konto löschen“. Danach darf der Nutzer in der Keycloak-Admin-Konsole (http://localhost:58080) nicht mehr existieren.
- [ ] **Dasselbe auf Android.** Das ist der größte Unsicherheitsfaktor, siehe Risiken 1 und 2 unten.
- [x] **Moderatorrolle prüfen** (30.09., per Token vom Client `stadtfest-tests`, alle drei Testnutzer korrekt): Mit `moderator@example.test` anmelden. `GET /v1/me` muss `roles: ["user","moderator"]` und `region.key = "ostalb"` liefern.
- [ ] **Maestro-Flow** `mobile/.maestro/login.yaml` grün bekommen (`make test-e2e`). Stand 30.09.: läuft bis „Mit E-Mail anmelden“ grün (Start jetzt per Deep Link). Danach öffnet sich der Browser nicht, weil `Crypto.digestStringAsync` (PKCE) auf dem überlasteten Mac (Load > 300 nach macOS-Update) minutenlang nicht zurückkommt. Auf ruhigem Rechner wiederholen; hängt es dort auch, ist es ein echter Fehler. Den Flow habe ich blind geschrieben. Wahrscheinliche Stellen zum Nachjustieren:
  - der iOS-Dialog „… möchte zum Anmelden verwenden“ (Text „Fortfahren“/„Continue“)
  - die Keycloak-Feld-IDs `username`, `password`, `kc-login`
  - Timeouts
- [ ] **Stille Token-Erneuerung testen:** Das Access-Token läuft nach 5 Minuten ab. Die App länger offen lassen und prüfen, dass Requests ohne Abmeldung weiterlaufen.
- [x] **Fehlerfall testen** (30.09., per API: `204`, `idp_deletion_deferred`, Retry nach 60 s löscht den Nutzer; auch Löschen bei laufendem Keycloak geprüft): Den Keycloak-Container stoppen und „Konto löschen“ auslösen. Die API muss `204` liefern, im Worker-Log erscheint `idp_deletion_deferred`. Nach dem Neustart von Keycloak löscht der Job den Nutzer (erster Retry nach 1 Minute).
- [ ] Nach erfolgreicher Prüfung: **diese Datei löschen**, PR-Beschreibung ergänzen, mergen (nur bei grüner Pipeline).

### Bekannte Risiken, die ich in der Cloud nicht prüfen konnte

1. **Android-Redirect:** Nach dem Login kommt `stadtfest://auth?code=…` zurück. Auf Android kann expo-router diesen Link zusätzlich als Route öffnen. Dafür gibt es die Auffangroute `mobile/src/app/auth.tsx`, die einfach zurücknavigiert.
   - Prüfen: Landet man nach dem Login wieder auf der Detailseite?
   - Wenn es flackert oder die Einstiegsseite doppelt schließt, ist die Alternative `+native-intent.tsx` mit `redirectSystemPath`.
2. **Retry nach `401` mit Request-Body:** `createAuthFetch` (`mobile/src/features/auth/session.ts`) klont den Request und baut ihn per `new Request(request, {headers})` neu.
   - In Jest (Node/undici) ist das getestet, im RN-Fetch-Polyfill nicht.
   - Prüfen: Name ändern mit abgelaufenem Token.
3. **`atob` für das ID-Token:** Damit werden E-Mail und Name aus dem ID-Token gelesen (`tokens.ts`). Hermes hat `atob`; falls nicht, bleibt die E-Mail im Drawer leer.
4. **Keycloak und `prompt=create`:** „Konto erstellen“ sendet `prompt=create`. Keycloak 26 kann das; falls die Registrierung nicht direkt aufgeht, in `config.ts` auf den Registrierungs-Link ausweichen.
5. **Apple/Google-Buttons:** Lokal gibt es in Keycloak keine IdPs `apple`/`google`; `kc_idp_hint` zeigt dann die normale Login-Seite. Echt testbar erst mit Zitadel.

### Später (nicht Teil dieses PRs)

- **Zitadel einrichten** nach [`00-docs/40-operations/zitadel.md`](00-docs/40-operations/zitadel.md): Projekt, Native-App mit PKCE, Apple/Google, Region-Action, Service-User. Die Spec empfiehlt, R16 (Produktion) teilweise vorzuziehen. Dabei prüfen:
  - Die Region-Action (`getMetadata().value`) liefert den Klartext, nicht base64.
  - Die Rollen erscheinen unter `urn:zitadel:iam:org:project:roles`.
- **AV-Vertrag mit Zitadel** vor dem Produktivstart.
- **Designlücke:** Einstiegs-Screen und Konto-Seite sind im Stil der bestehenden Screens gebaut. Später ins Design übernehmen (`00-docs/15-design`).
- **Offene Hooks für spätere Inkremente**, jeweils mit Kommentar im Code markiert:
  - R06: Favorit nach dem Login setzen (`executePendingAction` in `AuthProvider.tsx`) und Zeitleiste im Drawer.
  - R11: `DELETE /v1/me/devices/{token}` vor dem Abmelden.
  - R14: Einladung erneut öffnen (öffnet aktuell die Detailseite).
  - Jedes spätere Inkrement mit Personenbezug erweitert `SqlUserRepository.delete_personal_data`, das Löschkonzept und das VVT.
- Die Jest-Warnung „worker process has failed to exit gracefully“ gab es schon vor R05 auf `main`. Sie ist nicht von diesem Branch.

## 3. Was bereits getan wurde und warum

Vier Commits, jeweils mit grünem `make check`:

| Commit | Inhalt |
|---|---|
| `05e668e` | API-Spec + Codegen + neue Abhängigkeiten |
| `57ebbb2` | Backend: JWT, `/v1/me`, Kontolöschung, Tests |
| `57ffeeb` | App: Login, Session, Drawer, Konto-Seite, Tests |
| `2639486` | Doku: Datenschutz, ADR, Runbooks |

### API (API-first)

- `GET`, `PATCH` und `DELETE /v1/me` in `api/openapi.yaml`, danach `make gen`.
  - **Warum:** Laut CLAUDE.md ist die Spec der Vertrag; Schemathesis prüft die laufende App dagegen.
- `Me` enthält **keine E-Mail**.
  - **Warum:** Entscheidung E-08 (Datenminimierung). Die App liest die E-Mail nur aus dem ID-Token.

### Backend

- **Neuer Kontext `identity`** mit `domain/identity` (Principal, Namensregeln) und `application/identity` (Ports, Claim-Mapping, Use Cases).
  - **Warum:** Rollen- und Regionsprüfungen gehören in die Use Cases, nicht in Router. So gelten für REST, MCP und Worker dieselben Regeln.
- **Claim-Mapping konfigurierbar** über `AUTH_ROLES_CLAIM` und `AUTH_REGION_CLAIM`. Es liest sowohl Keycloak (`realm_access.roles`, Liste) als auch Zitadel (`urn:zitadel:iam:org:project:roles`, Objekt).
  - **Warum:** Lokal läuft Keycloak, in Produktion Zitadel (ADR 0003), und das mit derselben Codebasis.
- **Moderator ohne gültige Region verliert die Moderatorrolle** (Warnung im Log ohne Nutzerdaten).
  - **Warum:** So verlangt es die Spec (R05-US3); ein Moderator ohne Region darf nichts moderieren.
- **`JwksTokenVerifier`** (PyJWT):
  - erlaubt nur RS256/ES256 und prüft `iss`, `aud`, `exp`, `nbf`, `sub`; der Algorithmus muss zum Schlüsseltyp passen
  - cacht das JWKS und lädt es bei unbekannter `kid` neu, aber höchstens alle 30 s
  - findet das JWKS per OIDC-Discovery
  - **Warum:** Die Rotation bei unbekannter `kid` verlangt die Spec. Das Limit schützt davor, dass gefälschte `kid`s den IdP fluten. `none`/HS256 sind die klassischen JWT-Angriffe.
- **Jede Route prüft ein mitgesendetes Token**, auch öffentliche (`dependencies=[Depends(optional_principal)]` in `bootstrap/app.py`).
  - **Warum:** Laut Spec liefert ein ungültiges Token auch an öffentlichen Endpunkten `401`, damit der Client es erneuert. Ohne Token bleibt alles öffentlich nutzbar.
- **`GET /v1/me` legt den Nutzer beim ersten Aufruf an** (Upsert auf `sub`, sicher bei parallelen Aufrufen); Namen kommen aus `given_name`/`family_name`.
  - **Warum:** Eigene `/auth/*`-Endpunkte entfallen (E-01), das Konto entsteht also beim ersten API-Kontakt.
- **`DeleteAccount`** löscht zuerst die lokalen Daten in einer Transaktion und setzt `created_by`/`updated_by` auf null. Danach löscht es den IdP-Nutzer über den neuen **IdP-Admin-Port** (Keycloak Admin API, Zitadel User API v2, Fake für dev/test).
  - Scheitert der IdP-Aufruf, übernimmt der arq-Job `delete_idp_user` (Backoff 1 Minute bis 6 Stunden, 15 Versuche, ca. 2 Tage).
  - Lässt sich der Job nicht einreihen, antwortet die API mit `503`; ein erneuter Löschversuch ist unschädlich.
  - **Warum:** Art. 17 DSGVO und App-Store-Pflicht. Die lokale Löschung zuerst verhindert verwaiste personenbezogene Daten; der Retry deckt IdP-Ausfälle ab. Die Begründung steht in ADR 0010.
- **Migration `0003`**: Tabelle `app_user` (id, idp_subject, first_name, last_name, Zeitstempel).
- **Settings** validieren beim Start. In `prod` sind nur `https`-Issuer erlaubt, `IDP_ADMIN_PROVIDER=fake` ist dort verboten, und fehlende Admin-Credentials lassen den Start fehlschlagen.
  - **Warum:** Fail-fast laut CLAUDE.md, wie schon bei Geocoding.
- **Keycloak-Realm:** Der neue vertrauliche Client `stadtfest-admin` (Service-Account mit `manage-users`) dient der lokalen Kontolöschung.
- **`405`-Antworten** listen jetzt alle Methoden eines Pfads im `Allow`-Header.
  - **Warum:** `/v1/me` hat drei Routen auf demselben Pfad. FastAPI 0.141 nennt nur die erste, und Schemathesis hat das als Vertragsverletzung erkannt.
- **Tests:**
  - Unit: Claim-Mapping in beiden Formaten, Use Cases mit Fakes, JWKS mit lokal signierten Tokens (abgelaufen, falsches `aud`, fremder Schlüssel, `kid`-Rotation, HS256, `none`), REST, Admin-Adapter, Worker-Job, Settings
  - Log-Test: Tokens und Namen erscheinen nicht im Log
  - Integration: SQL-Repository und **echter Keycloak-Container** (Login-Roundtrip und Nutzerlöschung)

### App

- **Login per Authorization Code + PKCE** im System-Browser (`expo-auth-session`), Einstellungen in `features/auth/config.ts` und `oidc.ts`.
  - Apple (nur iOS) und Google springen per IdP-Hinweis direkt zum Anbieter.
  - „Konto erstellen“ nutzt `prompt=create`.
  - Abbruch bleibt ohne Toast, ein Fehler zeigt den Toast aus der Spec.
  - **Warum:** Das Backend fasst nie Passwörter an (CLAUDE.md); Formulare, Passwort-Reset und E-Mail-Bestätigung liegen im Hosted Login (R05-US1).
- **Tokens nur in `expo-secure-store`**, ein Schlüssel pro Token.
  - **Warum:** Spec R05-US2. Einige Android-Keystores warnen bei Werten über 2 KB.
- **`Session`** (`features/auth/session.ts`) mit zentralem Interceptor im API-Client (`api/client.ts`):
  - erneuert kurz vor Ablauf still
  - lässt parallele Requests auf **eine** Erneuerung warten
  - erneuert bei `401` einmal und wiederholt den Request
  - fällt bei abgelehntem Refresh-Token in den Gastmodus zurück (Toast); bei Netzfehlern bleibt die Sitzung erhalten
  - **Warum:** R05-US4; offline soll niemand abgemeldet werden.
- **`AuthProvider`**:
  - stellt die Sitzung beim Start wieder her und lädt `GET /v1/me`
  - führt die `pendingAction` aus
  - Logout widerruft das Refresh-Token beim IdP, löscht die Tokens, schließt den Seitenstapel und leert nur die nutzerbezogenen Queries (`/v1/me…`)
  - Konto löschen, Name ändern
  - Die IdP-Aufrufe sind injizierbar (`AuthGateway`) und damit testbar.
- **UI:**
  - Einstiegs-Screen `app/login.tsx` (Vollbild von unten, 380 ms)
  - Profil-Drawer mit Gastvariante (03-07) und angemeldeter Grundversion
  - Namens-Sheet, falls der IdP keinen Namen liefert (Apple)
  - Konto-Seite `app/konto.tsx` mit „Konto löschen“ und Bestätigungsdialog
  - Neue geteilte Komponenten mit Stories: `SideDrawer`, `TextField`, `Avatar`
  - **Warum:** R05-US1, US5 und US6. Komponenten ohne Story gelten laut CLAUDE.md nicht als fertig.
- Der `SideDrawer` animiert mit RN-`Animated`, nicht mit Reanimated.
  - **Warum:** Reanimated lässt sich in Jest nicht laden.
- **Tests (Jest):**
  - Session: paralleles Refresh, 401-Retry mit Body, Rückfall in den Gastmodus, Netzfehler
  - AuthProvider: pendingAction, Abbruch/Fehler, Wiederherstellung, Logout
  - Drawer, Namens-Sheet, Konto-Seite, Token-Speicher, Config
- **Maestro:** Flow `login.yaml` (noch nicht ausgeführt, siehe oben).

### Doku (Deutsch)

- VVT: Nr. 5 Nutzerkonto, Nr. 6 Anmeldung beim IdP, Tokens auf dem Gerät. Löschkonzept mit dem vollständigen Ablauf von `DeleteAccount`. Auftragsverarbeiter aktualisiert.
  - **Warum:** Laut CLAUDE.md müssen neue personenbezogene Felder im selben PR ins VVT.
- **ADR 0010** IdP-Admin-Port. In ADR 0003 ergänzt: In Zitadel ist die Audience die Projekt-ID, nicht `stadtfest-api`.
- Runbooks `zitadel.md` und `moderator-einrichten.md`; lokale Hinweise in `lokale-entwicklung.md`.
  - **Warum:** Neue externe Einrichtung braucht laut CLAUDE.md eine Schritt-für-Schritt-Anleitung.
- Architekturdiagramm: Pfeil „Kontolöschung · Admin-API“ ergänzt.

## 4. Nützliche Einstiegspunkte im Code

| Thema | Datei |
|---|---|
| Claim-Mapping | `backend/src/stadtfest/application/identity/claims.py` |
| Use Cases | `backend/src/stadtfest/application/identity/use_cases.py` |
| JWT-Prüfung | `backend/src/stadtfest/adapters/outbound/auth/jwks.py` |
| IdP-Admin | `backend/src/stadtfest/adapters/outbound/auth/idp_admin.py` |
| Retry-Job | `backend/src/stadtfest/adapters/inbound/worker/jobs.py` |
| Token-Handling REST | `backend/src/stadtfest/adapters/inbound/rest/auth.py` |
| App: OIDC-Konfiguration | `mobile/src/features/auth/config.ts` |
| App: Session/Interceptor | `mobile/src/features/auth/session.ts` |
| App: Auth-State | `mobile/src/features/auth/AuthProvider.tsx` |
| App: Drawer/Konto | `mobile/src/features/account/` |

## 5. Hinweise zur Umgebung der Cloud-Session

- Docker lief dort; die Integrationstests inklusive Keycloak-Container waren grün.
- `quay.io` war per Netzwerk-Policy gesperrt, deshalb lief der Test mit dem Keycloak-Image von Docker Hub (`keycloak/keycloak:26.4`, lokal als `quay.io/...` getaggt). In der CI und bei dir lokal gilt das Image aus `infra/compose.dev.yaml`.
- Es gab keinen Simulator; deshalb fehlen alle Prüfungen auf dem Gerät.
