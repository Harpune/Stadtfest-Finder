# R14 · Einladungen

| | |
|---|---|
| **Ziel** | Nutzer laden Freunde zu einem Fest ein. Eingeladene sagen zu oder ab, der Einladende sieht, wer kommt, und kann Offene erinnern. Freunde ohne App kommen über einen Einladungslink dazu. |
| **Hängt ab von** | R12 (Freunde), R11 (Benachrichtigungen) |
| **Quellen** | [06 Einladungen](../15-design/workflows/06-einladungen.md), [Design-Referenz §9](../15-design/design/design-referenz.md#9-einladung-einladung-einladung-neu-einladung-erhalten), Screens 06-01 bis 06-04, 02-04 („kommen mit“), 03-03 |
| **Bounded Context** | `collections` |
| **Rollen** | Nutzer als Einladender (Host) und als Eingeladener |

## Umfang

**Drin:**
- Einladung verfassen, Übersicht mit Zu- und Absagen, weitere einladen, erinnern
- Erhaltene Einladung beantworten und ändern
- Einladungslink
- Hinweis „… kommen mit“ auf der Detailseite
- Benachrichtigungen `invite`, `rsvp_yes`, `rsvp_no`, Absage-Fan-out an Zugesagte
- Teilen eines Fests für angemeldete Nutzer (Share-Sheet aus R04 freischalten)

## User Stories

### R14-US1 · Einstieg über „Einladen“
- Detailseite → „Einladen“ (Gast: Gast-Hinweis, R04):
  - `GET /v1/events/{id}/invitation` → eigene Einladung als Host oder `404`
  - bei `404`: Verfassen, sonst Übersicht
- „Einladen“ ist bei abgesagten und vergangenen Festen deaktiviert. Das Backend antwortet dort mit `422 event_not_invitable`.
- Auch **Teilen** (R04) ist jetzt für angemeldete Nutzer aktiv: natives Share-Sheet mit Titel, Zeitraum und `https://stadtfest-finder.de/f/{id}`.

### R14-US2 · Einladung verfassen und senden
- Screen 06-02:
  - Freundesliste mit Häkchen, bereits Eingeladene ausgeblendet
  - Nachricht (optional, max. 280)
  - „Freunde ohne App? Link teilen ↗“
- Der Button „Einladung senden ({n})“ ist ohne Auswahl deaktiviert.
- `POST /v1/events/{id}/invitation/invitees {userIds[], message?}` → `201 Invitation`:
  - Die Einladung wird bei Bedarf angelegt, eindeutig pro `(event, host)`.
  - `message` überschreibt die bisherige Nachricht nur, wenn sie gesetzt ist.
  - Nur Freunde des Hosts, sonst `422 not_a_friend`. Bereits Eingeladene werden ignoriert (idempotent).
- Jeder **neue** Eingeladene erhält `invite` („{Vorname} {Nachname} lädt dich zu {Fest} ein“). Push generisch: „Neue Einladung zu einem Fest“.
- Die App wechselt zur Übersicht, Toast „{n} Einladungen verschickt“. Die Mitteilungsberechtigung wird beim ersten Einladen abgefragt (R11-US5).

### R14-US3 · Einladungslink für Freunde ohne App
- `POST /v1/events/{id}/invitation/link` → `{url}` mit `https://stadtfest-finder.de/e/{token}` (eigenes Präfix, damit es nicht mit `/einladung/{id}` kollidiert). Legt die Einladung bei Bedarf an. Ein Token pro Einladung, rotierbar.
- Öffnen des Links: installierte App oder Store-Weiterleitung (R04-US6).
- Danach:
  - Gast → Gast-Hinweis „Freunde einladen“, danach Login mit `pendingAction {type: invitationLink, token}`
  - Angemeldet → Vorschau der Einladung → „Annehmen“ → `POST /v1/invitation-links/{token}/accept` → **Freundschaft mit dem Host wird angelegt** (falls nicht vorhanden) und der Nutzer wird Eingeladener mit Status `open`
- Danach öffnet sich die erhaltene Einladung (06-03). Der eigene Host-Link führt zur eigenen Übersicht.

### R14-US4 · Übersicht für den Einladenden
- Screen 06-01:
  - Kopf mit Bild und Fest
  - 3 Kacheln „kommen“ (Amber, Host zählt mit), „offen“, „abgesagt“ (Rosa)
  - Nachricht als Sprechblase
  - Gruppen „Kommen mit“ / „Noch keine Antwort“ / „Abgesagt“
- „Weitere einladen“ öffnet das Verfassen.
- „Erinnern“ → `POST /v1/invitations/{id}/reminders` → `202`:
  - Toast „Erinnerung an {n} Offene verschickt“ bzw. „Alle haben geantwortet“ (dann kein Aufruf)
  - höchstens 1× pro 24 h, sonst `429 {retryAfter}` → Toast „Du kannst erst morgen wieder erinnern“ (Annahme)
  - Event `invitation.reminded` → `invite`-Benachrichtigung an alle Offenen

### R14-US5 · Erhaltene Einladung beantworten
- Einstieg über Benachrichtigung, Push, Deep Link `…/einladung/{invitationId}` (nur für Eingeladene, sonst `404`) oder den Hinweis „… kommen mit“.
- `GET /v1/me/invitations/{id}` → Host, Zeitpunkt, Nachricht, Fest-Karte, andere Eingeladene mit Status, eigener Status. `GET /v1/me/invitations` liefert die Liste (für spätere Nutzung, kein eigener Screen).
- Screen 06-03: „{Name} lädt dich ein“, Buttons „Absagen“ und „Zusagen“ (Amber, flex 1.4).
- `PUT /v1/invitations/{id}/response {status: accepted|declined|open}`:
  - **Zusage** setzt serverseitig den Favoriten (idempotent), Banner „✓ Du hast zugesagt“ (06-04)
  - **Absage:** Banner „Du hast abgesagt“. Ein bestehender Favorit bleibt.
  - **„Ändern“** setzt auf `open` zurück, beide Buttons erscheinen wieder
  - Der Host erhält bei `accepted`/`declined` die Benachrichtigung `rsvp_yes` bzw. `rsvp_no` (Einstellung `rsvp`), Ziel ist die Übersicht. `open` erzeugt keine Benachrichtigung.
- Die Antwort ist nur möglich, solange das Fest nicht vergangen ist (`422`).

### R14-US6 · „… kommen mit“ auf der Detailseite
- `GET /v1/events/{id}` liefert mit Token `invitationSummary`:
  - **als Host:** zugesagte Eingeladene
  - **als zugesagter Eingeladener:** Host + weitere Zugesagte
  - Sonst `null`
- Die Detailseite zeigt „{Namen} kommen mit“ mit Avataren (max. 2 Namen, sonst „{A}, {B} und {n} weitere“). Ein Tipp öffnet die Übersicht bzw. die erhaltene Einladung.

### R14-US7 · Absage des Fests
- Der `event.cancelled`-Konsument (R11) bezieht zusätzlich alle Eingeladenen mit `accepted` ein (dedupliziert mit Favoriten).

## Daten

- `invitation`: `id`, `event_id`, `host_id`, `message`, `link_token?`, `created_at`, `last_reminder_at`, unique `(event_id, host_id)`.
- `invitee`: `invitation_id`, `user_id`, `status`, `responded_at`, PK `(invitation_id, user_id)`.

## Datenschutz

- Die Nachricht ist Freitext des Nutzers. Sie wird **nie geloggt** und nie an LLM oder Suche übergeben. Sichtbar ist sie nur für Host und Eingeladene.
- VVT „Einladungen“. Aufbewahrung: Einladungen werden 6 Monate nach Festende gelöscht (täglicher Job, Annahme).
- `DeleteAccount`: eigene Einladungen als Host löschen (inkl. Eingeladene), eigene `invitee`-Zeilen löschen, zugehörige Benachrichtigungen entfernen.

## Tests

- Unit: Einladbarkeit (abgesagt, vergangen), nur Freunde, Idempotenz, Erinnerungs-Limit, Zusage setzt Favoriten und Absage entfernt ihn nicht, `invitationSummary` je Rolle, Link-Annahme legt Freundschaft an.
- Integration: Fan-out Absage an Favoriten und Zugesagte ohne Doppelungen, Aufbewahrungs-Job.
- Contract: Einladungs-Endpunkte.
- RNTL: Verfassen (Button deaktiviert), Übersicht (Zähler), Erhalten (Banner, Ändern).
- Maestro: A lädt B ein → B sagt per Benachrichtigung zu → A sieht „B kommt mit“ auf der Detailseite und einen Eintrag „Zusage“.

## Definition of Done

- [ ] Screens 06-01 bis 06-04 und der „kommen mit“-Hinweis (02-04) umgesetzt, dunkel und hell.
- [ ] Teilen für angemeldete Nutzer aktiv, Gast-Aktionen `share`/`invite` werden nach dem Login nachgeholt.
- [ ] Deep Links `/einladung/{id}` und `/e/{token}` funktionieren beim Kalt- und Warmstart.
- [ ] VVT und `DeleteAccount` erweitert.

## Umsetzungsnotizen (09.10.2026)

- **Teilen:** ist seit der Entscheidung vom 29.09.2026 (R04-US3a) auch für Gäste aktiv. R14 ändert daran nichts; eine nachgeholte Gast-Aktion `share` entfällt. Nachgeholt werden `invite` (öffnet die eigene Einladung) und `invitationLink` (der Link-Screen bleibt offen und zeigt nach dem Login die Vorschau).
- **Einladungslink:** Die API liefert nur das Token (`{token}`), die App baut `https://{EXPO_PUBLIC_LINK_HOST}/e/{token}` wie beim Freundschaftslink (R12). Ein Token pro Einladung, es bleibt bestehen.
- **Ziel der Benachrichtigungen:** `invite` öffnet die erhaltene Einladung (`invitation`, ID der Einladung), `rsvp_yes`/`rsvp_no` die eigene Übersicht (`invitationOverview`, ID des Fests).
- **„… kommen mit“:** Der Hinweis erscheint erst, wenn mindestens eine Person zugesagt hat. Als Eingeladener mit Zusage zählen Host und weitere Zugesagte.
- **Erinnern:** Ohne Offene zeigt die App „Alle haben geantwortet“ ohne Aufruf. Innerhalb von 24 h antwortet die API mit `429 reminded_recently` und `fields.retryAfter` (Sekunden).
- **Antworten** sind wie das Einladen nur bei veröffentlichten, nicht vergangenen Festen möglich (`422 event_not_invitable`), also auch nicht bei abgesagten.
- **Absage-Fan-out:** `event.cancelled` erreicht Favoriten-Inhaber und Zugesagte, dedupliziert.
