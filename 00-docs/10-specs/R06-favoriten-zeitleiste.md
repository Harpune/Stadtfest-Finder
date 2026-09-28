# R06 · Favoriten und Zeitleiste

| | |
|---|---|
| **Ziel** | Nutzer merken sich Feste per Herz und sehen ihre Festsaison chronologisch im Profil-Drawer. Der Drawer wird zum Einstieg in alle persönlichen Bereiche. |
| **Hängt ab von** | R05 |
| **Quellen** | [04 Favoriten und Zeitleiste](../15-design/workflows/04-favoriten-und-zeitleiste.md), [Design-Referenz §7](../15-design/design/design-referenz.md#7-profil-drawer-drawer-drawer-vergangen-drawer-gast-drawer-leer), Screens 04-01 bis 04-05, 02-04 |
| **Bounded Context** | `collections` |
| **Rollen** | Nutzer, Moderator |

## Umfang

**Drin:** Favoriten-API, Herz auf Detailseite, in der Liste und im Karussell (falls gestaltet), Zeitleiste mit Vergangenen, Leerzustand, Dunkelmodus-Umschalter, Link „Moderator-Ansicht“ (sichtbar für die Rolle `moderator`, Ziel ab R07), `isFavorite` in der Detailantwort.

**Nicht drin:**
- Karte „Gemeinsame Listen“ im Drawer: erst ab R13, bis dahin ausgeblendet
- Zähler „Benachrichtigungen“: erst ab R11, bis dahin ausgeblendet
- Abfrage der Mitteilungsberechtigung beim ersten Favoriten (R11)

## User Stories

### R06-US1 · Favorit setzen und entfernen
- `PUT /v1/me/favorites/{eventId}` → `204`, idempotent. `DELETE` → `204`, ebenfalls idempotent.
- Nur für öffentlich sichtbare Feste (veröffentlicht oder abgesagt, auch vergangen). Sonst `404`.
- `event.favorite_count` wird in derselben Transaktion angepasst.
- **App:** optimistisch. Das Herz füllt sich sofort, Toast „Zu Favoriten hinzugefügt“ bzw. „Aus Favoriten entfernt“. Bei Fehler wird zurückgesetzt, Toast „Das hat nicht geklappt“.
- Favoriten-Status in Liste und Karussell: Die App gleicht gegen die geladene Favoritenliste ab. Die öffentliche, gecachte Suche bleibt nutzerneutral (R02-US6).
- `GET /v1/events/{id}` liefert mit Token zusätzlich `isFavorite`. Antworten mit Token werden nie gecacht.
- Als Gast: Gast-Hinweis (R04). Nach dem Login wird der gemerkte Favorit gesetzt.

### R06-US2 · Favoriten laden
- `GET /v1/me/favorites?include=past` → `{items: FavoriteEntry[]}` mit Fest-Zusammenfassung (`EventSummary` + `status`, `categoryName`, `emoji`) und `favoritedAt`.
- Gelöschte Feste fehlen. Abgesagte erscheinen mit Status, vergangene nur mit `include=past`.
- Sortierung nach `startDate` aufsteigend.
- Die App hält die Favoriten als **eine Query**, die Zeitleiste, Herzen und Detailseite gemeinsam nutzen. Eine Änderung auf der Karte erscheint ohne Neuladen in der Zeitleiste.

### R06-US3 · Zeitleiste „Deine Festsaison“
- Überschrift (Serif 28) und „{n} Favoriten stehen an“.
- Vertikaler Zeitstrahl der **zukünftigen und laufenden** Favoriten, gruppiert nach Monat (Serif 14, Rosa).
- Eintrag: Punkt mit rosa Rand, Datum, Name (Serif 17), „{Emoji} {Kategorie} · {Ort}“. Abgesagte mit Status „Abgesagt“.
- **Laufend** (Beginn ≤ heute ≤ Ende): Karte in `accentSoft` mit Amber-Rand, leuchtendem Punkt und „● Läuft · noch X Tage“.
- „↑ Vergangene einblenden ({n})“ blendet die vergangenen Favoriten ausgegraut oberhalb ein, getrennt durch „HEUTE · {Wochentag} {Datum}“ in Rosa. Der Button wechselt zu „↓ Vergangene ausblenden“.
- Ein Tipp auf einen Eintrag schließt den Drawer und öffnet die Detailseite.
- **Leerzustand (04-03):** gestrichelte Box, Herz-Icon, „Noch keine Favoriten“, Erklärung und „Feste entdecken“ (schließt den Drawer).

### R06-US4 · Drawer-Fußbereich
- **Schalter Dunkelmodus:** Standard folgt dem System. Der Schalter überschreibt das dauerhaft auf dem Gerät. Ein langer Druck bzw. ein Menüeintrag „Wie System“ setzt die Überschreibung zurück (Annahme).
- **„Moderator-Ansicht“** in Amber, nur mit der Rolle `moderator`. Führt ab R07 in die Moderationsansicht.
- **„Abmelden“** in Rosa (aus R05).
- Drawer: 336 breit, von rechts, Scrim, Nutzerzeile mit Deckkraft .85.

## Daten

`favorite`: `user_id`, `event_id`, `created_at`, PK `(user_id, event_id)`, FK mit `ON DELETE CASCADE` auf Nutzer und Fest.

## Datenschutz

- `DeleteAccount` löscht die Favoriten und passt `favorite_count` an.
- VVT „Favoriten“: Zweck Merkliste und Erinnerungen. Aufbewahrung bis zur Löschung durch den Nutzer oder das Konto. Vergangene Favoriten bleiben (Zeitleiste). Vorschlag: nach 24 Monaten nach Festende automatisch löschen (Job ab R11).

## Tests

- Unit: Idempotenz, Zähler, `404` für Entwürfe.
- Integration: `favorite_count` bei parallelen `PUT`, Cascade beim Löschen eines Nutzers.
- Contract: Favoriten-Endpunkte.
- RNTL: Zeitleiste (Gruppierung, laufend, vergangen, leer), optimistisches Update mit Rollback.
- Maestro `favorites.yaml`: Login → Detail → Herz → Drawer zeigt das Fest → Herz entfernen → Leerzustand.

## Definition of Done

- [ ] Screens 04-01 bis 04-05 und 02-04 (ohne „kommen mit“) umgesetzt, dunkel und hell.
- [ ] Die Gast-Aktion „Favorit“ wird nach dem Login nachgeholt.
- [ ] `DeleteAccount` erweitert, VVT aktualisiert.
