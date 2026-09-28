# API-Endpunkte

Vorschlag einer REST-API, abgeleitet aus den Workflows. Alle Pfade beginnen mit `/v1`, Formate sind JSON, Zeitangaben ISO 8601 (Europe/Berlin), Koordinaten WGS84.

**Auth:** `–` öffentlich · `U` angemeldeter Nutzer · `M` Rolle Moderator (bei Festen zusätzlich nur eigene Region).
**Modus:** siehe [README](../README.md#konventionen-in-den-workflow-dokumenten).

## Öffentlich (Gast und Nutzer)

| Methode | Pfad | Auth | Zweck | Modus | Workflow |
|---|---|---|---|---|---|
| GET | `/events?bbox=&lat=&lon=&radiusKm=&from=&to=&months=&categories=&q=&cursor=` | – | Feste für Karte und Liste. Nur veröffentlicht oder abgesagt, Ende ≥ heute. | sync | 01 |
| GET | `/events/count?…` | – | Trefferzahl für Filter-Vorschau und Radius-Vorschau | sync | 01, 07 |
| GET | `/events/{id}` | – / U | Detail. Mit Token zusätzlich `isFavorite`, `invitationSummary`. | sync | 02 |
| GET | `/categories` | – | Aktive Kategorien, sortiert (ETag, cachebar) | sync | 01 |
| GET | `/geocode?q=&country=DE` | – | Orts- und PLZ-Suche | sync | 07, 08, 09 |
| GET | `/geocode/reverse?lat=&lon=` | – | Adresse zu Koordinaten | sync | 07, 08 |

## Authentifizierung

| Methode | Pfad | Auth | Zweck | Modus | Workflow |
|---|---|---|---|---|---|
| POST | `/auth/oauth/{apple\|google}` | – | Anmelden/Registrieren per ID-Token | sync | 03 |
| POST | `/auth/register` | – | Registrieren per E-Mail. Die Bestätigungs-E-Mail wird im Hintergrund verschickt. | sync + async | 03 |
| POST | `/auth/login` | – | Anmelden per E-Mail/Passwort | sync | 03 |
| POST | `/auth/refresh` | – | Access-Token erneuern | sync | 03 |
| POST | `/auth/logout` | U | Refresh-Token widerrufen, Gerät abmelden | sync | 03 |
| POST | `/auth/password-reset` | – | Link per E-Mail (immer `202`) | async | 03 |
| GET | `/me` | U | Profil inkl. `roles[]`, `regionId` | sync | 03, 04 |
| POST | `/me/devices` | U | Push-Token registrieren `{token, platform}` | sync | 03 |
| DELETE | `/me/devices/{token}` | U | Push-Token entfernen | sync | 03 |

## Favoriten, Freunde, Listen

| Methode | Pfad | Auth | Zweck | Modus | Workflow |
|---|---|---|---|---|---|
| GET | `/me/favorites?include=past` | U | Favoriten für die Zeitleiste | sync | 04 |
| PUT | `/me/favorites/{eventId}` | U | Favorit setzen (idempotent) | sync | 01, 02, 04 |
| DELETE | `/me/favorites/{eventId}` | U | Favorit entfernen | sync | 01, 02, 04 |
| GET | `/me/friends` | U | Freunde für Listen und Einladungen | sync | 05, 06 |
| GET | `/lists` | U | Eigene gemeinsame Listen | sync | 05 |
| POST | `/lists` | U | Liste anlegen `{name, memberIds[]}`. Neue Mitglieder bekommen eine Benachrichtigung. | sync + async | 05 |
| GET | `/lists/{id}` | U (Mitglied) | Liste mit Mitgliedern und Festen | sync | 05 |
| PATCH | `/lists/{id}` | U (Mitglied) | Umbenennen | sync | 05 |
| DELETE | `/lists/{id}` | U (Mitglied) | Liste löschen | sync | 05 |
| POST | `/lists/{id}/members` | U (Mitglied) | Mitglied hinzufügen `{userId}` | sync + async | 05 |
| DELETE | `/lists/{id}/members/{userId}` | U (Mitglied) | Mitglied entfernen / Liste verlassen | sync | 05 |
| PUT | `/lists/{id}/events/{eventId}` | U (Mitglied) | Fest hinzufügen | sync | 05 |
| DELETE | `/lists/{id}/events/{eventId}` | U (Mitglied) | Fest entfernen | sync | 05 |

## Einladungen

| Methode | Pfad | Auth | Zweck | Modus | Workflow |
|---|---|---|---|---|---|
| GET | `/events/{id}/invitation` | U | Eigene Einladung zu diesem Fest (Übersicht) oder `404` | sync | 02, 06 |
| POST | `/events/{id}/invitation/invitees` | U | Freunde einladen `{userIds[], message}`. Legt die Einladung bei Bedarf an und benachrichtigt die Eingeladenen. | sync + async | 06 |
| POST | `/events/{id}/invitation/link` | U | Teilbarer Einladungslink | sync | 06 |
| POST | `/invitations/{id}/reminders` | U (Einladender) | Offene erinnern (höchstens 1× / 24 h) | async | 06 |
| GET | `/me/invitations` · `/me/invitations/{id}` | U | Erhaltene Einladungen | sync | 06, 07 |
| PUT | `/invitations/{id}/response` | U (Eingeladener) | `{status: accepted\|declined\|open}`. Eine Zusage setzt den Favoriten, der Einladende wird benachrichtigt. | sync + async | 06 |

## Benachrichtigungen

| Methode | Pfad | Auth | Zweck | Modus | Workflow |
|---|---|---|---|---|---|
| GET | `/me/notifications?cursor=` | U | Liste, neueste zuerst, `unreadCount` im Header | sync | 07 |
| POST | `/me/notifications/{id}/read` | U | Als gelesen markieren | sync | 07 |
| POST | `/me/notifications/read-all` | U | Alle als gelesen markieren | sync | 07 |
| GET | `/me/notification-settings` | U | Einstellungen | sync | 07 |
| PUT | `/me/notification-settings` | U | `{remind, remindDaysBefore, near, home{name,plz,lat,lon}, nearRadiusKm, change, invite, rsvp}` | sync | 07 |

## Moderation: Feste (Rolle M, eigene Region)

| Methode | Pfad | Zweck | Modus | Workflow |
|---|---|---|---|---|
| GET | `/mod/events?status=&q=&ids=` | Feste der Region, alle Status, mit `favoriteCount`, `source` | sync | 08, 09 |
| GET | `/mod/events/{id}` | Fest zum Bearbeiten (mit `version`) | sync | 08 |
| POST | `/mod/events` | Anlegen (immer Entwurf) | sync | 08 |
| PATCH | `/mod/events/{id}` | Bearbeiten (`If-Match: version`) | sync; bei veröffentlichten Festen + async (`event.updated`) | 08, 09 |
| POST | `/mod/events/{id}/publish` | Veröffentlichen. Prüft die Pflichtfelder (`422` mit Feldliste). | sync + async (`event.published`) | 08, 09 |
| POST | `/mod/events/{id}/unpublish` | Zurück auf Entwurf | sync + async | 08 |
| POST | `/mod/events/{id}/cancel` | Absagen `{reason}` | sync + async (`event.cancelled`) | 08 |
| DELETE | `/mod/events/{id}` | Löschen (Soft-Delete) | sync + async (`event.deleted`) | 08, 09 |
| POST | `/mod/uploads` | Signierte Upload-URL `{contentType}` → `{uploadId, url}` | sync | 08 |
| POST | `/mod/events/{id}/images` | Hochgeladenes Bild zuordnen `{uploadId, position}`. Thumbnails werden im Hintergrund erzeugt. | sync + async | 08 |
| DELETE | `/mod/events/{id}/images/{imageId}` | Bild entfernen | sync | 08 |
| PUT | `/mod/events/{id}/images/order` | Reihenfolge (erstes = Titelbild) | sync | 08 |

## Moderation: KI-Suche (Rolle M)

| Methode | Pfad | Zweck | Modus | Workflow |
|---|---|---|---|---|
| POST | `/mod/ai-searches` | `{plz}` → `202 {jobId, status}`. `409`, wenn bereits ein Job läuft. | **async** | 09 |
| GET | `/mod/ai-searches?status=running` | Laufende Jobs (Leiste nach App-Neustart) | sync | 09 |
| GET | `/mod/ai-searches/{jobId}` | Status und Ergebnis `{status, newEventIds[], skipped{duplicate, outOfRegion}}` | sync (Polling) | 09 |

Abschluss zusätzlich per Push an das Gerät des Moderators (`ai_search.completed`) oder per Server-Sent Events (`GET /mod/events/stream`).

## Moderation: Kategorien (Rolle M, app-weit)

| Methode | Pfad | Zweck | Modus | Workflow |
|---|---|---|---|---|
| GET | `/mod/categories` | Alle, inkl. inaktiver, mit `eventCount` | sync | 10 |
| POST | `/mod/categories` | Anlegen `{name, emoji, color, active}` (ans Ende sortiert) | sync + async (Cache) | 10 |
| PATCH | `/mod/categories/{id}` | Bearbeiten | sync + async (Cache) | 10 |
| PUT | `/mod/categories/order` | `{ids[]}` in neuer Reihenfolge | sync + async (Cache) | 10 |
| DELETE | `/mod/categories/{id}?replacementId=` | Löschen. Hat die Kategorie Feste, ist `replacementId` Pflicht, sonst `422`. | sync + async (Index, Cache) | 10 |

## Fehlerformat

```json
{ "error": "validation_failed", "message": "Bitte fülle die markierten Pflichtfelder aus", "fields": { "startDate": "required", "address": "required" } }
```

| Status | Bedeutung | Reaktion im Client |
|---|---|---|
| 401 | nicht angemeldet / Token ungültig | Token erneuern, sonst Gast-Hinweis |
| 403 | Rolle fehlt | Moderationsansicht schließen, Toast |
| 404 | nicht vorhanden oder fremde Region | Hinweis „nicht mehr verfügbar“ |
| 409 | Konflikt (Version, laufender Job, E-Mail vergeben) | Hinweis mit Neuladen |
| 422 | Validierung | Feldfehler anzeigen |
| 429 | Rate-Limit | Toast „Bitte kurz warten“ |
