# R07 · Moderation: Feste

| | |
|---|---|
| **Ziel** | Moderatoren pflegen die Feste ihrer Region in einer klar abgegrenzten Moderationsansicht: anlegen, bearbeiten, als Entwurf speichern, veröffentlichen, zurückziehen, absagen und löschen. Änderungen wirken sofort auf die Nutzeransicht. |
| **Hängt ab von** | R06 |
| **Quellen** | [08 Moderation: Feste](../15-design/workflows/08-moderation-feste.md), [Ereignisse und Jobs](../15-design/backend/ereignisse-und-jobs.md), [Design-Referenz §11, §12](../15-design/design/design-referenz.md#11-moderator-übersicht-der-feste-mod-feste), Screens 08-01 bis 08-03 und 08-05 bis 08-11 |
| **Bounded Context** | `moderation` (Use Cases), `events` (Aggregat) |
| **Flow** | C6–C8 (Prüfen und Freigeben) |
| **Rollen** | Moderator (nur eigene Region) |

## Umfang

**Drin:**
- Moderationsansicht mit Banner und Tab-Leiste (Tab „Kategorien“ ab R09)
- Übersicht mit Suche und Status-Chips, Formular mit allen Feldern außer Bildern, Ort per Adresse oder Pin, Programm
- Statusmodell, Validierung, optimistische Sperre
- Transactional Outbox, Domain-Events inkl. Konsumenten für Cache und Aufräumen

**Nicht drin:**
- Bilder (R08)
- Benachrichtigungen als Folge von Veröffentlichen, Ändern und Absagen (R11). Die Events werden hier schon erzeugt.
- KI-Funde (R10)

## User Stories

### R07-US1 · Moderationsansicht betreten und verlassen
- Drawer → „Moderator-Ansicht“ → Moderationsansicht mit Türkis-Akzent:
  - festes Banner „MODERATOR-ANSICHT · Region {Name} · {Vorname Nachname}“ mit „Beenden“
  - Tab-Leiste „📅 Feste | 🏷️ Kategorien“ (Kategorien ab R09)
- „Beenden“ kehrt in die Nutzeransicht zurück, Toast. Karte und Liste laden neu (Katalog-Generation hat sich ggf. geändert).
- Liefert ein Mod-Endpunkt `403`, schließt die App die Moderationsansicht mit Toast.

### R07-US2 · Übersicht der Feste der Region
- `GET /v1/mod/events?status=&q=&ids=` liefert alle Feste der eigenen Region (außer gelöschten) mit `favoriteCount`, `source`, `version`.
- Der abgeleitete Status `past` gilt für veröffentlichte Feste mit Ende < heute.
- Titel „Feste“, Buttons „Suchen“ (öffnet die KI-Suche ab R10, bis dahin ausgeblendet) und „+ Neues Fest“.
- Suchfeld „Fest oder Ort in deiner Region“ und Status-Chips mit Anzahl: Alle, Entwurf, Veröffentlicht, Vergangen, Abgesagt. Gefiltert wird clientseitig auf der geladenen Liste.
- Sortierung: anstehende aufsteigend, danach vergangene absteigend.
- Zeile:
  - Datumsblock und Name (abgesagte durchgestrichen)
  - „{Emoji} {Ort} · {Zeitraum}“, Status-Pill
  - ggf. „Automatisch gefunden“ und „♥ {n}“
  - vergangene mit Deckkraft .6
- Skeleton beim Laden, Leerzustand „Keine Feste gefunden“.

### R07-US3 · Fest anlegen und bearbeiten
- **Neu:** leeres Formular, „Status: Entwurf“.
- **Bearbeiten:** `GET /v1/mod/events/{id}` mit allen Feldern und `version`.
- Felder laut Design §12 (ohne Bilder): Name *, Kurzname (optional, Standard = Name gekürzt auf 18 Zeichen, Annahme), Kategorie * (nur aktive), Beginn * / Ende *, Öffnungszeiten, Ort *, Beschreibung, Programm, Eintritt, Anfahrt (ÖPNV, Parken), Website.
- **Ort:** Segment „Adresse | Pin auf Karte“.
  - Adresse: `GET /v1/geocode` (debounced), die Karte springt zum Ergebnis.
  - Pin: Ein Tipp setzt den Pin (Türkis-Rand, Hinweis „Tippe, um den Pin zu setzen“). Ohne Adresse wird per `GET /v1/geocode/reverse` gefüllt, sonst „Pin {lat}, {lon}“.
  - Aus dem Geocoding werden `postalCode` und `city` übernommen.
- **Programm:** Zeilen „Tag, Zeit“ und „Programmpunkt“, ✕, „+ Programmpunkt“. Gespeichert wird mit dem Fest.
- `POST /v1/mod/events` legt **immer einen Entwurf** an (`regionId` = Region des Moderators).
- `PATCH /v1/mod/events/{id}` mit `If-Match: {version}` (Merge-Patch, Programm wird als Ganzes ersetzt). Bei Versionskonflikt: `409` → Dialog „Dieses Fest wurde inzwischen geändert“ mit „Neu laden“.

### R07-US4 · Validierung
| Feld | Entwurf | Veröffentlichen | Fehlertext |
|---|---|---|---|
| Name | ✓ | ✓ | „Bitte gib einen Namen ein.“ |
| Kategorie | – | ✓, aktiv | „Bitte wähle eine Kategorie.“ |
| Beginn | – | ✓ | „Bitte wähle den Beginn.“ |
| Ende | – | ✓, ≥ Beginn | „Bitte wähle das Ende.“ / „Das Ende liegt vor dem Beginn.“ |
| Adresse oder Pin | – | ✓, Koordinaten vorhanden, PLZ ∈ Region | „Bitte gib eine Adresse ein oder setze einen Pin.“ / „Der Ort liegt außerhalb deiner Region.“ |
| Website | – | wenn gesetzt: http(s)-URL | „Bitte gib eine gültige Web-Adresse ein.“ |

- Die Regeln liegen in der Domain (`Event.can_publish()`) und gelten für App, Backend und MCP.
- Die App prüft vorab: rote Rahmen, Feldtexte, Toast „Bitte fülle die markierten Pflichtfelder aus“.
- Das Backend antwortet mit `422 {error: validation_failed, fields}` bzw. `422 region_mismatch`.
- Längenlimits (Annahme): Name 120, Beschreibung 5.000, Öffnungszeilen 10 × 80, Programm 50 Zeilen.

### R07-US5 · Statuswechsel
| Aktion | Endpunkt | Von → nach | Event | Toast |
|---|---|---|---|---|
| Als Entwurf | `PATCH` (+ `POST …/unpublish`, wenn veröffentlicht) | pub → draft | `event.unpublished` | „Als Entwurf gespeichert“ bzw. „Zurück auf Entwurf gesetzt · für Nutzer ausgeblendet“ |
| Veröffentlichen | `PATCH` + `POST …/publish` | draft → pub | `event.published` | „Veröffentlicht · jetzt in der App sichtbar“ |
| Änderungen veröffentlichen | `PATCH` auf pub | pub → pub | `event.updated {changedFields}` | „Änderungen veröffentlicht“ |
| Absagen | `POST …/cancel {reason?}` | pub → cancelled | `event.cancelled` | „Abgesagt · {n} Nutzer werden benachrichtigt“ |
| Löschen | `DELETE …` | alle → gelöscht (soft) | `event.deleted` | „Fest gelöscht“ |

- Absagen ist nur für veröffentlichte Feste möglich. Abgesagte Feste lassen sich nur noch in Textfeldern bearbeiten (Beschreibung, Öffnungszeiten, Eintritt, Anfahrt, Website, Absagegrund). Eine Wiederaufnahme ist nicht vorgesehen. Unerlaubte Übergänge ergeben `409 invalid_transition`.
- `publishedAt` wird beim ersten Veröffentlichen gesetzt.
- **⋯-Menü (08-08):** „⚠️ Fest absagen“ (nur bei veröffentlichten), „🗑️ Fest löschen“.
- **Absage-Dialog (08-09):** „Fest absagen?“, „{favoriteCount} Nutzer mit diesem Favoriten werden benachrichtigt.“, optionaler Grund (max. 500), „Absagen und benachrichtigen“ (Rosa).
- **Lösch-Dialog (08-10):** „Endgültig löschen“. Mit Favoriten folgt der Hinweis, dass Nutzer nicht benachrichtigt werden und Absagen die bessere Wahl ist.

### R07-US6 · Region-Scoping
- Alle `/v1/mod/events*`-Use-Cases prüfen: Rolle `moderator` (sonst `403`) und `event.regionId == principal.regionId` (sonst **`404`**).
- `?ids=` liefert nur Feste der eigenen Region, fremde IDs fallen stillschweigend weg.

### R07-US7 · Domain-Events und Folgen
- **Transactional Outbox (E-13):** Tabelle `outbox` (`id`, `type`, `payload` nur mit IDs, `occurred_at`, `dispatched_at`). Die Events werden in derselben Transaktion wie die Änderung geschrieben.
- Ein Relay im Worker (Polling 1 s bzw. `LISTEN/NOTIFY`) reiht sie in arq ein. Konsumenten sind idempotent (Event-ID).
- **Konsumenten in R07:**
  - `event.published|updated|unpublished|cancelled|deleted` → Katalog-Generation erhöhen (Cache-Invalidierung).
  - `event.deleted` → Favoriten, später Listeneinträge, Einladungen und Bilder des Fests entfernen. `favorite_count` bleibt als historischer Wert.
- `event.updated` enthält `changedFields`. R11 benachrichtigt nur bei `startDate`, `endDate`, `openingHours`, `address`, `location`.

## Daten

- `event` erhält die Pflege-Felder aus dem Datenmodell (`created_by`, `updated_by`, `published_at`, `cancel_reason`, `deleted_at`, `version`).
- `outbox` wie oben. Aufbewahrung versendeter Einträge: 14 Tage (Aufräum-Job).

## Datenschutz

- Audit-Felder enthalten Nutzer-IDs. `DeleteAccount` setzt sie auf `null` (R05-US6).
- Freitexte von Moderatoren (Beschreibung usw.) sind öffentliche Festdaten und dürfen keine Personendaten enthalten. Hinweis im Formular: „Keine personenbezogenen Daten eintragen“ (Annahme).

## Tests

- Unit: Statusautomat (alle erlaubten und verbotenen Übergänge), `can_publish` mit allen Fehlerfällen inkl. Region, `changedFields`-Ermittlung, Autorisierung (`403`, `404` fremde Region).
- Integration: Outbox → Relay → Konsument (Generation erhöht, Cache leer), optimistische Sperre (`409`), Soft-Delete räumt Favoriten ab.
- Contract: alle Mod-Endpunkte inkl. `If-Match`.
- RNTL: Formular-Validierung, Pin-Modus, Absage- und Lösch-Dialog.
- Maestro `moderator-publish.yaml`: Login als Moderator → Moderator-Ansicht → „+ Neues Fest“ → Pflichtfelder → Veröffentlichen → Beenden → Fest ist auf der Karte zu sehen.

## Definition of Done

- [ ] Screens 08-01 bis 08-03 und 08-05 bis 08-11 umgesetzt (08-04 ohne Bilder), dunkel und hell.
- [ ] Veröffentlichte Feste erscheinen sofort in der Gast-Suche, zurückgezogene und gelöschte verschwinden sofort (Cache-Test).
- [ ] Die Maestro-Flows „Moderator veröffentlicht“ und „Gastsuche“ sind grün.
- [ ] Architektur-Doku um die Outbox ergänzt.
