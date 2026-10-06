# R11 · Benachrichtigungen und Push

| | |
|---|---|
| **Ziel** | Nutzer werden über relevante Ereignisse informiert: Erinnerung, neues Fest am Wohnort, Änderung, Absage. Jede Art ist einzeln steuerbar. Die Push-Infrastruktur steht für die folgenden Inkremente (Freunde, Listen, Einladungen) bereit. |
| **Hängt ab von** | R07 (Domain-Events). Für den Moderator-Push: R10. |
| **Quellen** | [07 Benachrichtigungen](../15-design/workflows/07-benachrichtigungen.md), [Ereignisse und Jobs](../15-design/backend/ereignisse-und-jobs.md), [CLAUDE.md „Push notifications“](../../CLAUDE.md), Screens 07-01 bis 07-04. Entscheidungen E-04, E-09, E-10. |
| **Bounded Context** | `notifications` (neu, eigener Kontext, siehe offene Punkte) |
| **Rollen** | Nutzer. Moderator für `ai_search.*`. |

## Umfang

**Drin:**
- Benachrichtigungsliste, gelesen/ungelesen, Einstellungen inkl. Wohnort und Radius
- Push-Port mit den Adaptern `expo`, `direct` (APNs/FCM) und `disabled`
- Geräte-Registrierung, Token-Pflege
- Arten `remind`, `near`, `change`, `cancel` sowie der Moderator-Push `ai_search_completed|failed`
- Zähler am Profilbild und im Drawer
- Deep Links aus dem Push

**Nicht drin:** Die Arten `invite`, `rsvp_yes`, `rsvp_no` (R14), `list_added` (R13) und `friend_added` (R12). Diese Inkremente registrieren ihre Arten im hier gebauten Mechanismus.

## User Stories

### R11-US1 · Benachrichtigungsliste
- Drawer → „Benachrichtigungen“ (mit rosa Zähler) → Liste (07-01):
  - Gruppen „Neu“ (ungelesen) und „Früher“, dazu „Alle als gelesen markieren“
  - Eintrag: Icon-Kachel mit Symbol der Art, Art-Zeile, Text (ungelesen fett auf `surface` mit rosa Punkt), relative Zeit
- `GET /v1/me/notifications?cursor=&limit=` → `{items: [{id, type, text, target: {type, id}, read, createdAt}], nextCursor}`, Header `X-Unread-Count`, neueste zuerst.
- **Der Text wird beim Lesen erzeugt** (E-09) aus der Art und den referenzierten Daten, mit deutschen Vorlagen aus dem Design, z. B. „📍 Neu an deinem Wohnort: {Festname} in {Ort}“.
- Ist ein referenziertes Fest gelöscht, entfällt der Eintrag in der Antwort.
- Ein Tipp markiert den Eintrag als gelesen (`POST /v1/me/notifications/{id}/read`, optimistisch) und öffnet das Ziel (Detailseite, ab R14 auch Einladungen).
- `POST /v1/me/notifications/read-all`: Alle Punkte und Zähler verschwinden.
- Leerzustand „Noch keine Benachrichtigungen“ (Annahme).

### R11-US2 · Einstellungen
- `GET /v1/me/notification-settings` und `PUT` (ganzes Objekt):

  ```json
  {"remind": true, "remindDaysBefore": 1, "near": true,
   "home": {"postalCode": "73430", "placeName": "Aalen"} ,
   "nearRadiusKm": 25, "change": true, "invite": true, "rsvp": true}
  ```

  Das Backend speichert zusätzlich den PLZ-Mittelpunkt aus dem Geocoding. Die App schickt keine Koordinaten (E-10).
- **Standard:** alle Arten aktiv, Erinnerung 1 Tag vorher, Radius 25 km, Wohnort leer.
- **Validierung:** `remindDaysBefore ∈ {1,3,7}`, `nearRadiusKm` 5–150 in 5er-Schritten, `home.postalCode` muss geocodierbar sein (`422`).
- **App (07-02, 07-03):**
  - ein Schalter pro Art (48 × 28, an = Amber), sofort wirksam, `PUT` debounced und optimistisch
  - Erinnerungszeitpunkt „1 Tag vorher | 3 Tage | 1 Woche“
  - Wohnort per Stadt oder PLZ mit Vorschlägen ab 2 Zeichen (`/v1/geocode`)
  - „Aktuellen Standort verwenden“: GPS → `/v1/geocode/reverse` → Vorschlag der PLZ. Die GPS-Position wird danach verworfen.
  - Radius-Schieber mit Vorschau „Aktuell {n} Feste im Umkreis von {r} km um {Ort}“ über `/v1/events/count`
  - Ohne Wohnort ist „Neu an deinem Wohnort“ ausgegraut, mit Hinweis „Lege zuerst deinen Wohnort fest“
- Hinweis unter den Schaltern: „Stumm geschaltete Arten erscheinen weiterhin in der Liste“.
- Der Eintrag „Konto löschen“ zieht von der Konto-Seite (R05) zusätzlich hierher (Design-Hinweis aus 03).

### R11-US3 · Zustellung
- Ablauf: Domain-Event bzw. Zeitplan → Empfänger ermitteln → Eintrag speichern (`read=false`) → wenn die Art aktiv ist: Push → Zustellergebnis auswerten (ungültiger Token → Gerät entfernen).
- **Push-Inhalt (E-04, CLAUDE.md):**
  - Titel und Text generisch je Art, ohne Namen, Festnamen oder Orte, z. B. „Erinnerung“ / „Eines deiner Lieblingsfeste beginnt bald.“
  - Payload `{notificationId, type, targetType, targetId}` (flach mit Zeichenketten, weil FCM nur solche Werte erlaubt; Moderator-Push ohne `notificationId`)
  - Badge = Anzahl ungelesener Einträge
- **Idempotenz:**
  - höchstens eine Erinnerung pro `(user, event, Tag)`
  - höchstens eine Änderungsmeldung pro `(user, event, Stunde)` (zusammengefasst)
  - ein Eintrag pro `(user, Domain-Event-ID)`
- Fan-out in Batches (z. B. 500 Empfänger pro Job), damit große Absagen den Worker nicht blockieren.

### R11-US4 · Arten und Auslöser
| Art | Auslöser | Empfänger | Einstellung |
|---|---|---|---|
| `remind` | Cron täglich 09:00 Europe/Berlin | Favoriten mit `startDate = heute + remindDaysBefore` | `remind` |
| `near` | `event.published` (nur beim **ersten** Veröffentlichen) | `near=true`, Wohnort gesetzt, `ST_DWithin(home, event, nearRadiusKm)` | `near` |
| `change` | `event.updated` mit Änderungen an `startDate`, `endDate`, `openingHours`, `address` oder `location` | alle mit diesem Favoriten | `change` |
| `cancel` | `event.cancelled` | alle mit diesem Favoriten (ab R14 auch Zugesagte, dedupliziert) | `change` |
| `ai_search_completed` / `ai_search_failed` | `ai_search.*` | der startende Moderator, **nur Push, kein Listeneintrag** (Annahme) | immer |

- Ab R11 zeigt der Absage-Toast in R07 die tatsächliche Empfängerzahl.

### R11-US5 · Geräte und Berechtigung
- Die Mitteilungsberechtigung fragt die App **beim ersten Favoriten** bzw. bei der ersten Einladung ab, nicht beim Start.
- Nach der Berechtigung und nach jedem Login: `POST /v1/me/devices {token, platform, provider}`. Der Token-Typ passt zu `PUSH_PROVIDER`: Expo-Push-Token bei `expo`, `getDevicePushTokenAsync` bei `direct`. Die App erfährt den Provider über `GET /v1/config` (öffentlich, neu).
- Beim Logout: `DELETE /v1/me/devices/{token}`.
- Ein täglicher Job entfernt ungültige Tokens (Receipts bzw. APNs/FCM-Fehler) und Geräte ohne Aktivität seit 90 Tagen.
- **Push empfangen:** Im Vordergrund erscheint ein Toast und der Zähler steigt. Ein Tipp auf den Push öffnet das Ziel per Deep Link (auch beim Kaltstart). Der Zähler aktualisiert sich beim App-Start und beim Empfang.

## Konfiguration

```bash
PUSH_PROVIDER=disabled        # expo | direct | disabled
EXPO_ACCESS_TOKEN=            # expo
APNS_KEY_ID= APNS_TEAM_ID= APNS_KEY_PATH=     # direct
FCM_PROJECT_ID= FCM_CREDENTIALS_PATH=         # direct
```

Fehlende Credentials für den gewählten Anbieter beenden den Start. `disabled` ist der Standard für lokal und Tests.

## Daten

| Tabelle | Felder |
|---|---|
| `notification` | `id`, `user_id`, `type`, `event_id?`, `dedupe_key` (Idempotenz, eindeutig je Nutzer), `read`, `pushed`, `created_at`. `invitation_id`, `list_id` und `actor_user_id` kommen mit R12–R14. |
| `notification_settings` | Felder laut Datenmodell, `home_postal_code`, `home_place_name`, `home_location geography(Point)` = PLZ-Mittelpunkt |
| `device` | `user_id`, `token` (unique), `platform`, `provider`, `last_seen_at` |

## Datenschutz

- VVT-Einträge: Benachrichtigungen, Push (Anbieter Expo/APNs/FCM, ADR für Nicht-EU), Wohnort.
- **Aufbewahrung:** Benachrichtigungen 12 Monate (täglicher Lösch-Job), Geräte bis Logout oder 90 Tage Inaktivität, Einstellungen bis zur Kontolöschung.
- `DeleteAccount` löscht Benachrichtigungen (eigene und solche, in denen der Nutzer `actor` ist), Einstellungen und Geräte.
- Push-Payloads enthalten nur IDs und generische Texte (Test prüft alle Vorlagen).

## Tests

- Unit:
  - Empfängerermittlung je Art
  - Idempotenzregeln (Erinnerung pro Tag, Änderung pro Stunde)
  - `change` nur bei relevanten Feldern
  - `near` nur beim ersten Veröffentlichen
  - Textvorlagen
  - Push-Payload ohne personenbezogene Daten
- Integration: Cron-Job mit fester Uhr, `ST_DWithin`-Abfrage, Fan-out mit 2.000 Empfängern, Adapter `expo` und `direct` gegen HTTP-Stubs (keine echten Dienste), Entfernen ungültiger Tokens.
- Contract: Benachrichtigungs-, Einstellungs- und Geräte-Endpunkte.
- RNTL: Liste (Gruppen, gelesen), Einstellungen (ausgegraut ohne Wohnort, Radius-Vorschau).
- Maestro: Nutzer setzt Favoriten → Moderator sagt das Fest ab → Nutzer sieht den Eintrag „Fest abgesagt“ und den Zähler.

## Doku/Betrieb

- ADR: Push-Anbieter und Nicht-EU-Verarbeiter (Expo, APNs, FCM).
- `40-operations/push-expo.md`, `40-operations/push-apns-fcm.md`: Schlüssel und Zertifikate erzeugen, hinterlegen, testen, Rollback auf `disabled`.

## Definition of Done

- [x] Screens 07-01 bis 07-04 umgesetzt (Liste mit Ziehen zum Aktualisieren, Einstellungen mit Wohnort, Radius und Vorschau, Hell und Dunkel über die Theme-Tokens), Zähler am Profilbild (Punkt) und im Drawer.
- [ ] Zustellung mit allen drei `PUSH_PROVIDER`-Werten durch Tests belegt (erledigt), manuell mit `expo` auf einem Gerät geprüft (offen: braucht EAS-Projekt, Firebase-Konfiguration und `EXPO_ACCESS_TOKEN`, siehe [push-expo.md](../40-operations/push-expo.md)).
- [x] VVT, Löschkonzept und `DeleteAccount` erweitert.

## Entscheidungen bei der Umsetzung

- **Kontext:** fünfter Kontext `notifications` ([ADR 0016](../25-adr/0016-benachrichtigungen-und-push.md)), CLAUDE.md und Architektur angepasst.
- **Push-Adapter:** `expo`, `direct` (APNs und FCM, für beide Plattformen gleich; APNs braucht HTTP/2, dafür das Paket `h2`) und `disabled`. Neue Abhängigkeiten nach Rückfrage am 06.10.2026: `h2` (Backend), `expo-notifications` (App).
- **„Neu an deinem Wohnort“ nur beim ersten Veröffentlichen:** `event.published` trägt `firstPublication: true`, wenn das Fest zum ersten Mal öffentlich wird.
- **Idempotenz** über `dedupe_key`: `remind:<fest>:<Tag>`, `change:<fest>:<Stunde>`, `near:<fest>`, `cancel:<fest>` (Tag und Stunde in Europe/Berlin).
- **App:** `expo-notifications`; die Berechtigung fragt die App beim ersten Favoriten, in den Einstellungen gibt es „Mitteilungen erlauben“ bzw. den Weg in die Systemeinstellungen. Ohne EAS-Projekt-ID (Expo) bzw. Firebase-Konfiguration (Android) bekommt die App kein Token; die Liste funktioniert trotzdem. „Konto löschen“ steht zusätzlich unten in den Einstellungen.
- **Listentexte** entstehen beim Lesen aus Art und aktuellen Festdaten, z. B. „{Fest} beginnt morgen: 2.–13. Okt 2026 in Aalen.“, „Neu in Aalen: {Fest} (…)“, „{Fest} (…) fällt aus. Grund: …“.

## Offene Punkte

- Die Arten `rsvp`, `invite` und `list_added` bekommen in ihren Inkrementen eigene Vorlagen.
