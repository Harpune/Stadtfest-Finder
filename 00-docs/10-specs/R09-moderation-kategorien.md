# R09 · Moderation: Kategorien

> **Hinweis (05.10.2026):** Die Moderationsregionen wurden abgeschafft ([ADR 0015](../25-adr/0015-regionen-abgeschafft.md)). Angaben zu Regionen in diesem Inkrement sind überholt.

| | |
|---|---|
| **Ziel** | Kategorie-Admins pflegen die app-weiten Kategorien (Name, Emoji, Farbe, Reihenfolge, aktiv) und löschen sie mit Ersatzkategorie. Die Chips und Marker-Farben in der App folgen sofort. |
| **Hängt ab von** | R07 |
| **Quellen** | [10 Moderation: Kategorien](../15-design/workflows/10-moderation-kategorien.md), [Design-Referenz §13, §14](../15-design/design/design-referenz.md#13-moderator-kategorien-verwalten-mod-kategorien), Screens 10-01 bis 10-04. Entscheidung E-06. |
| **Bounded Context** | `events` (Kategorie), `moderation` (Use Cases) |
| **Rollen** | Rolle `category_admin` schreibt. `moderator` ohne `category_admin` liest nur. |

## Umfang

**Drin:** Tab „Kategorien“ in der Moderationsansicht, Übersicht mit Vorschau und Drag & Drop, Formular mit Live-Vorschau, Aktiv-Schalter, Löschen mit Ersatzkategorie, Cache-Invalidierung.

## User Stories

### R09-US1 · Übersicht
- `GET /v1/mod/categories` (Rolle `moderator` oder `category_admin`): alle Kategorien inkl. inaktiver, sortiert, mit `eventCount`. Gezählt werden Feste aller Regionen und Status außer gelöschten.
- Tab „🏷️ Kategorien“ zeigt:
  - Titel, „+ Neu“ und eine Erklärung
  - „Vorschau Startseite“ mit den aktiven Chips in aktueller Reihenfolge
  - Zeilen mit Griff, Emoji-Kreis in der Kategorie-Farbe, Name und „{n} Feste“ bzw. „Deaktiviert · {n} Feste“ (Deckkraft .5)
- **Ohne `category_admin`:** kein „+ Neu“, keine Griffe. Ein Tipp öffnet das Formular schreibgeschützt mit dem Hinweis „Nur Kategorie-Admins können Kategorien ändern.“

### R09-US2 · Reihenfolge per Drag & Drop
- Die Zeile hebt sich ab (Schatten, Türkis-Rand), die anderen rücken nach (200 ms).
- Beim Loslassen: `PUT /v1/mod/categories/order {ids[]}`. Die Liste muss vollständig sein und alle IDs enthalten, sonst `422`.
- Optimistisch, Toast „Reihenfolge gespeichert · Chips auf der Startseite aktualisiert“, bei Fehler zurücksetzen.
- Bibliotheksvorschlag: `react-native-draggable-flatlist` oder eine eigene Lösung mit Reanimated und Gesture Handler. Vor der Einführung abstimmen.

### R09-US3 · Anlegen und bearbeiten
- Formular (10-02, 10-03):
  - Vorschau von Chip und Karten-Marker, live
  - Name *
  - Emoji-Raster mit 12 Vorgaben (🎪 🎡 🎄 🐎 🍺 🍷 🎭 🎶 🏰 🎃 🌸 🔥)
  - Farbe aus 6 Vorgaben (`#FFB547 #FF6B8B #5EEAD4 #8B9CFF #7ED957 #C792EA`)
  - Schalter „Aktiv“
- `POST /v1/mod/categories {name, emoji, color, active}`: Neue Kategorien kommen ans Ende. `PATCH /v1/mod/categories/{id}`.
- **Serverseitige Validierung:**
  - Name 1–40 Zeichen, eindeutig (case-insensitive) → „Bitte gib einen Namen ein.“ / „Diesen Namen gibt es schon.“
  - Emoji und Farbe nur aus den Vorgaben
- **Deaktivieren:** Die Kategorie erscheint nicht mehr als Chip. Zugeordnete Feste bleiben sichtbar. Neue Veröffentlichungen mit dieser Kategorie sind nicht erlaubt (R07-US4).

### R09-US4 · Löschen
- **Ohne Feste:** einfache Bestätigung → `DELETE /v1/mod/categories/{id}`.
- **Mit Festen:** Dialog mit Radio-Liste der übrigen Kategorien. Der Button zeigt „Ersatz wählen“ (deaktiviert), nach der Wahl „Löschen und verschieben“.
- `DELETE …?replacementId=` verschiebt die Feste und löscht die Kategorie **in einer Transaktion**. Ohne `replacementId` bei vorhandenen Festen gibt es `422`, ebenso bei `replacementId == id`.
- Toast „Gelöscht · {n} Feste nach ‚{X}‘ verschoben“.
- Eine gelöschte Kategorie ist physisch weg (kein Soft-Delete). Gelöschte Feste (soft) werden mit umgehängt.

### R09-US5 · Wirkung auf die App
- Alle Änderungen erzeugen `category.changed` (Outbox) → Konsument invalidiert den Cache von `GET /v1/categories` (neues `ETag`) und erhöht bei Löschen/Verschieben die Katalog-Generation.
- Die App lädt Kategorien beim Start und danach spätestens nach 15 min neu (TanStack `staleTime`). Das Zurückkehren aus der Moderationsansicht lädt sofort neu.
- Gesetzte Filter auf gelöschte oder deaktivierte Kategorien entfallen stillschweigend (R03-US6).

## Tests

- Unit: Autorisierung (`moderator` ohne `category_admin` → `403` bei allen schreibenden Aktionen), Löschen mit/ohne Ersatz, Reihenfolge-Validierung, eindeutiger Name.
- Integration: Transaktion beim Verschieben (Fehler mittendrin → nichts geändert), ETag-Wechsel nach Änderung.
- Contract: Kategorien-Endpunkte.
- RNTL: Formular-Vorschau, Lösch-Dialog, Nur-Lesen-Modus.
- Maestro: Kategorie-Admin deaktiviert „Weihnachtsmarkt“ → Beenden → Chip ist weg.

## Doku/Betrieb

- `40-operations/moderator-einrichten.md` um die Rolle `category_admin` ergänzen.
- Rollen und Rechte im Design als geklärt markieren (Verweis auf E-06).

## Definition of Done

- [ ] Screens 10-01 bis 10-04 umgesetzt, dunkel und hell.
- [ ] Rollenprüfung per Test für REST belegt.
- [ ] Die Chips auf der Startseite ändern sich nach einer Kategorie-Änderung ohne App-Neuinstallation.
