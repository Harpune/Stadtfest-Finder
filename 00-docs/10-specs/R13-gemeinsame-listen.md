# R13 · Gemeinsame Listen

| | |
|---|---|
| **Ziel** | Nutzer legen mit Freunden gemeinsame Festlisten an (z. B. „Weihnachtsmarkt-Tour 2026“) und pflegen sie gemeinsam. |
| **Hängt ab von** | R12 |
| **Quellen** | [05 Gemeinsame Listen](../15-design/workflows/05-gemeinsame-listen.md), [Design-Referenz §8](../15-design/design/design-referenz.md#8-gemeinsame-favoritenlisten-listen-liste-detail-liste-bearbeiten), Screens 05-01 bis 05-04 |
| **Bounded Context** | `collections` |
| **Rollen** | Nutzer (Listenmitglied) |

## Umfang

**Drin:** Übersicht, Anlegen, Ansehen, Bearbeiten (Name, Mitglieder, Feste), Löschen, Liste verlassen, Karte „Gemeinsame Listen“ im Drawer, Benachrichtigung `list_added`.

## User Stories

### R13-US1 · Übersicht und Drawer-Karte
- Die Drawer-Karte „Gemeinsame Listen“ zeigt 3 überlappende Avatare und „{n} Listen · {Namen}“. Ohne Listen erscheint „Plane Festbesuche mit Freunden“ (Annahme).
- `GET /v1/lists` → `[{id, name, eventCount, members: [{id, firstName, lastName}], nextEvent?: EventSummary}]`, sortiert nach nächstem Fest, danach nach Name.
- Übersicht (05-01): Zurück, „Gemeinsame Listen“, „+ Neu“, Hinweis „Plant Festbesuche zusammen. …“. Karten mit Name, Anzahl Feste, Avataren, „{n} Personen“ und nächstem Fest. Leerzustand „Noch keine Listen“.

### R13-US2 · Liste anlegen
- Sheet (05-02): Namensfeld und Freundesliste mit Häkchen (`GET /v1/me/friends`). „Liste erstellen“ ist erst mit Namen aktiv.
- `POST /v1/lists {name, memberIds[]}` → `201 List`. Der Ersteller ist automatisch Mitglied. `memberIds` müssen **Freunde des Erstellers** sein, sonst `422 not_a_friend`. Name 1–60 Zeichen.
- Neue Mitglieder erhalten `list_added` („{Vorname} hat dich zur Liste ‚{Name}‘ hinzugefügt“) mit Push, gesteuert über die Einstellung `invite` (Annahme). Ziel ist die Liste.
- Die App öffnet danach die neue Liste, Toast „Liste erstellt“.

### R13-US3 · Liste ansehen
- `GET /v1/lists/{id}` → Name, Mitglieder, Feste (chronologisch, inkl. vergangener und abgesagter). **Nicht-Mitglieder bekommen `404`.**
- Screen (05-03):
  - Titel (Serif 30)
  - Mitglieder als Avatare 48 mit „+ Hinzufügen“
  - „Feste · chronologisch“ mit Datumsblock (Tag in Rosa), vergangene mit Deckkraft .5, abgesagte mit Status
  - „+ Fest hinzufügen“
- Ein Tipp auf ein Fest öffnet die Detailseite.
- Gelöschte Feste verschwinden (Aufräumen über `event.deleted`, R07).

### R13-US4 · Mitglieder und Feste pflegen
- **Mitglieder:** Sheet mit Mehrfachauswahl der eigenen Freunde. Jede Änderung wirkt sofort und optimistisch:
  - `POST /v1/lists/{id}/members {userId}` (nur Freunde des Handelnden, idempotent, erzeugt `list_added`)
  - `DELETE /v1/lists/{id}/members/{userId}`
- **Feste:** Sheet mit anstehenden Festen. Oben stehen die eigenen Favoriten, darüber ein Suchfeld für alle öffentlichen Feste (nutzt `GET /v1/events?q=`) (Annahme, statt „alle anstehenden“). Mehrfachauswahl:
  - `PUT /v1/lists/{id}/events/{eventId}` (nur öffentlich sichtbare Feste, idempotent)
  - `DELETE …/events/{eventId}`
- Einzeloperationen statt Ersetzen der ganzen Liste. Dadurch entstehen keine Konflikte bei gleichzeitiger Bearbeitung.
- Alle Mitglieder haben dieselben Rechte (kein Ersteller-Sonderrecht).

### R13-US5 · Bearbeiten, löschen, verlassen
- „Bearbeiten“ (05-04):
  - Name wird zum Eingabefeld
  - ✕ an Mitgliedern (nicht am eigenen Account) und Festen
  - „Liste löschen“ (Rosa), „Fertig“ (Amber)
- Name speichern beim Verlassen des Felds bzw. mit „Fertig“: `PATCH /v1/lists/{id} {name}`.
- „Liste löschen“ → Bestätigung → `DELETE /v1/lists/{id}` → zurück zur Übersicht, Toast „Liste gelöscht“. Jedes Mitglied darf löschen (laut Design).
- **„Liste verlassen“** (Annahme, nicht gestaltet): im Bearbeiten-Modus → `DELETE /v1/lists/{id}/members/{me}`. Verlässt das letzte Mitglied die Liste, wird sie gelöscht.

## Daten

`shared_list` (`id`, `name`, `created_by?`, `created_at`), `list_member` (`list_id`, `user_id`, `added_by?`, `added_at`), `list_event` (`list_id`, `event_id`, `added_by?`, `added_at`). FKs mit Cascade auf Liste bzw. Fest.

## Datenschutz

- Mitglieder sehen Vor- und Nachname der anderen Mitglieder (Zweck: gemeinsame Planung). VVT-Eintrag „Gemeinsame Listen“.
- `DeleteAccount`: Mitgliedschaften löschen, `created_by`/`added_by` auf `null`, Listen ohne Mitglieder löschen, `list_added`-Benachrichtigungen mit diesem Akteur entfernen.

## Tests

- Unit: Mitgliedschaftsprüfung (`404`), nur Freunde hinzufügbar, letzte Person verlässt → Liste gelöscht, eigenes Entfernen nur über „Verlassen“.
- Integration: gleichzeitiges Hinzufügen und Entfernen durch zwei Mitglieder, Cascade bei gelöschtem Fest.
- Contract: Listen-Endpunkte.
- RNTL: Übersicht (leer, voll), Bearbeiten-Modus.
- Maestro: Liste anlegen mit Freund → Fest hinzufügen → Freund (zweiter Account) sieht die Liste und den Eintrag in der Benachrichtigungsliste.

## Definition of Done

- [ ] Screens 05-01 bis 05-04 und die Drawer-Karte umgesetzt, dunkel und hell (Farben nur aus Theme-Tokens). Offen: Prüfung auf dem Gerät.
- [x] Autorisierung per Test belegt (`404` für Nicht-Mitglieder in allen Use Cases, nur Freunde hinzufügbar).
- [x] VVT und `DeleteAccount` erweitert.

## Entscheidungen bei der Umsetzung

- **Benachrichtigung:** `list_added` speichert Liste (`list_id`) und Auslöser (`actor_user_id`); der Text „{Vorname} hat dich zur Liste ‚{Name}‘ hinzugefügt“ entsteht beim Lesen. Das Ereignis `list.members_added` geht über die Outbox (gleiche Transaktion wie die Mitgliedschaft). Push nur bei aktivierter Einstellung „Einladungen“. Neue Art und Zieltyp `list` laut [ADR 0017](../25-adr/0017-erweiterbare-benachrichtigungsarten.md) in der Ignore-Liste von oasdiff.
- **Feste einer Liste:** Gelöschte und zurückgezogene Feste werden beim Lesen ausgeblendet (wie bei Favoriten), die Zeilen bleiben bis zum endgültigen Löschen des Fests (FK mit Cascade).
- **Verlassen:** `DELETE /v1/lists/{id}/members/{eigene ID}`; das Entfernen sperrt die Liste kurz, damit zwei gleichzeitig Austretende die Liste sicher löschen.

## Offene Punkte

- Sollen Mitglieder über Änderungen an einer Liste benachrichtigt werden? Vorerst nur beim Hinzufügen.
