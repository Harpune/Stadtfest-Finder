# R02 · Katalog-Backend

> **Hinweis (05.10.2026):** Die Moderationsregionen wurden abgeschafft ([ADR 0015](../25-adr/0015-regionen-abgeschafft.md)). Angaben zu Regionen in diesem Inkrement sind überholt.

| | |
|---|---|
| **Ziel** | Das Datenmodell für Feste, Kategorien und Regionen steht. Die öffentliche Lese-API liefert veröffentlichte Feste für Karte, Liste und Detailseite. Geocoding läuft über Nominatim. Synthetische Seed-Daten machen alles lokal sichtbar. |
| **Hängt ab von** | R01 |
| **Quellen** | [Datenmodell](../15-design/backend/datenmodell.md), [API](../15-design/backend/api-endpunkte.md), [01 Suche](../15-design/workflows/01-stadtfest-suche.md), [02 Details](../15-design/workflows/02-fest-details.md) |
| **Bounded Context** | `events` |
| **Flow** | A (Suche als Gast) |

## Umfang

**Drin:**
- Entitäten `Category`, `Region`, `Event`, `ProgramItem` sowie die Tabelle `EventImage` (leer, befüllt ab R08)
- `GET /v1/categories`, `GET /v1/events`, `GET /v1/events/count`, `GET /v1/events/{id}`, `GET /v1/geocode`, `GET /v1/geocode/reverse`
- Cache-Port mit Redis-Adapter, Geocoding-Port mit Nominatim-Adapter
- Seed-Daten

**Nicht drin:** Schreibende Endpunkte (→ R07), nutzerbezogene Felder in der Detailantwort (`isFavorite` → R06, `invitationSummary` → R14).

## User Stories

### R02-US1 · Kategorien abrufen
Als App will ich die aktiven Kategorien in Moderationsreihenfolge laden, um Chips und Marker-Farben anzuzeigen.

- `GET /v1/categories` liefert nur aktive Kategorien, sortiert nach `sortOrder`: `[{id, name, emoji, color, sortOrder}]`.
- Die Antwort trägt einen `ETag` und `Cache-Control: public, max-age=900`. `If-None-Match` ergibt `304`.
- Redis-Cache mit TTL 1 h. Invalidierung ab R09.

### R02-US2 · Feste für Karte und Liste suchen
Als Gast will ich Feste in einem Kartenausschnitt bzw. Umkreis finden, gefiltert nach Zeitraum, Kategorie und Text.

`GET /v1/events` mit diesen Parametern:

| Parameter | Bedeutung |
|---|---|
| `bbox=minLon,minLat,maxLon,maxLat` | optional, Kartenausschnitt |
| `lat`, `lon`, `radiusKm` | optional, Umkreis 10–300 (Standard 150). Bezugspunkt für die Entfernung. |
| `when` | `all` (Standard) \| `today` \| `weekend` \| `months` |
| `months` | kommagetrennt `YYYY-MM`, Pflicht bei `when=months`, maximal 12 |
| `categories` | kommagetrennte IDs. Unbekannte oder inaktive IDs werden **stillschweigend ignoriert** ([10](../15-design/workflows/10-moderation-kategorien.md) Regeln). |
| `q` | ab 2 Zeichen, sucht in Name, Kurzname, Ort und Stadt. Groß-/Kleinschreibung und Akzente zählen nicht (`unaccent`), Tippfehler werden toleriert (`pg_trgm`). |
| `cursor`, `limit` | Paging, `limit` Standard 50, maximal 500 (Karte) |

**Sichtbarkeit:** nur `status ∈ {published, cancelled}` und `endDate ≥ heute (Europe/Berlin)`. Gelöschte Feste (`deletedAt`) nie.

**Zeitraum-Semantik:**
- `today`: Das Fest läuft heute.
- `weekend`: Das Fest überschneidet sich mit Samstag oder Sonntag der laufenden Woche. Ist heute Sonntag, zählt nur Sonntag.
- `months`: Das Fest überschneidet sich mit mindestens einem gewählten Monat.

**Sortierung:** laufende zuerst, dann nach `startDate` aufsteigend, bei Gleichstand nach Name.

**Antwort:** `{items: EventSummary[], nextCursor}`. `EventSummary` enthält:
- `id`, `name`, `shortName`, `status`
- `startDate`, `endDate`, `place`, `city`
- `lat`, `lon`, `categoryId`
- `distanceKm` (zum Bezugspunkt `lat/lon`, sonst zur bbox-Mitte)
- `coverImage {url, thumbUrl}?` (ab R08)

Die abgeleiteten Status-Texte („Läuft · noch X Tage“, „In X Tagen“, „Ab …“) berechnet der Client.

**Validierung:** `422` bei ungültiger bbox, Radius außerhalb 10–300, `when=months` ohne `months` oder `q` mit 1 Zeichen.

### R02-US3 · Treffer zählen
Als App will ich die Trefferzahl für den Filter-Button und die Chip-Zahlen, ohne Feste zu laden.

- `GET /v1/events/count` mit denselben Parametern wie `GET /v1/events`.
- Antwort `{total, byCategory: {categoryId: n}}`.
- `byCategory` zählt je Kategorie die Feste, die **alle anderen Filter außer dem Kategorie-Filter** erfüllen (Chip-Zahl laut 01 Schritt 7).

### R02-US4 · Fest-Detail
- `GET /v1/events/{id}` liefert `EventDetail` mit allen Feldern aus [02 Inhalte](../15-design/workflows/02-fest-details.md#inhalte-und-datenfelder):
  - Kopf: `category {id, name, emoji, color}`, `name`, `place`, `address`, `city`, `postalCode`, `lat`, `lon`
  - Termine und Preis: `startDate`, `endDate`, `openingHours[]`, `price`
  - Texte: `description`, `program[] {date, timeLabel, title, subtitle}` (sortiert), `transit`, `parking`, `websiteUrl`
  - Status: `status`, `cancelReason`
  - `images[]` (leer bis R08)
- Optionaler Parameter `lat/lon` für `distanceKm`.
- `404`, wenn das Fest nicht existiert, gelöscht ist oder nicht öffentlich sichtbar ist (Entwurf). **Vergangene veröffentlichte Feste sind per ID weiter abrufbar**, weil Zeitleiste und Listen darauf verlinken.

### R02-US5 · Geocoding über Nominatim
Als App will ich Orte bzw. PLZ suchen und Koordinaten in einen Ort auflösen, ohne selbst mit Nominatim zu sprechen.

- `GET /v1/geocode?q=&limit=` (ab 2 Zeichen) → `[{label, postalCode?, city, lat, lon, kind: postcode|city|address}]`, nur Deutschland (`countrycodes=de`). Eine reine 5-stellige Eingabe wird als strukturierte PLZ-Suche (`postalcode=`) geschickt.
- `GET /v1/geocode/reverse?lat=&lon=` → `{postalCode, city, label}`.
- **Geocoding-Port** in `application/`, Adapter `adapters/outbound/geocoding/nominatim` (httpx, Timeout 3 s, eigener User-Agent). Dazu ein Fake-Adapter mit festen Daten für Tests und lokal.
- Redis-Cache: vorwärts 30 Tage (Schlüssel = normalisierte Anfrage). Reverse-Ergebnisse werden auf einem gerundeten Raster gecacht (3 Nachkommastellen); die Originalkoordinaten landen nicht im Cache-Schlüssel.
- Ist Nominatim nicht erreichbar, gibt es `503` mit `error: geocoding_unavailable`. Die Suche nach Festen ist davon nicht betroffen.
- Rate-Limit pro Client-IP: 5 Anfragen/s, sonst `429`. Die IP wird nur flüchtig in Redis gezählt und nicht geloggt.

### R02-US6 · Cache für Gast-Suchen
- Cache-Port (`get/set/delete/bump_namespace`) mit Redis-Adapter. Domain-Code cacht nie.
- `GET /v1/events` und `/count` werden für Anfragen **ohne Token** 5 min gecacht. Der Schlüssel besteht aus den normalisierten Parametern plus Katalog-Generation. `lat/lon` werden dafür auf 2 Nachkommastellen gerundet, bbox-Werte auf 3; die Ergebnisse berechnen trotzdem die exakten Entfernungen, sie werden nur beim Cachen gerundet.
- Die **Katalog-Generation** (Zähler in Redis) wird bei jeder Veröffentlichungsänderung erhöht (ab R07). Damit sind alle Suchcaches auf einen Schlag ungültig.

### R02-US7 · Seed-Daten
Als Entwickler will ich mit `make seed` realistische, aber synthetische Daten laden.

- 5 Kategorien wie im Design: Stadtfest, Volksfest & Kirmes, Weihnachtsmarkt, Markt & Messe, Weinfest (inaktiv), mit Farben und Emojis aus der Design-Referenz.
- Region `ostalb` mit PLZ-Liste (Aalen und Umgebung) und eine zweite Region, um die Regionsgrenzen zu testen.
- ≈ 40 Feste um Aalen und in Süddeutschland mit Koordinaten und PLZ im Seed (kein Geocoding beim Seeden). Status gemischt: veröffentlicht, Entwurf, abgesagt, vergangen, mit Programm.
- **Datumsangaben relativ zu heute**, damit die Daten immer aktuell sind (z. B. „läuft seit 3 Tagen“, „beginnt in 8 Tagen“).
- Der Seed ist idempotent: erneutes Ausführen setzt den Stand zurück.

## Daten

| Tabelle | Felder (Auswahl) | Hinweise |
|---|---|---|
| `category` | `id`, `name`, `emoji`, `color`, `active`, `sort_order`, `created_at`, `updated_at` | `name` eindeutig (case-insensitive) |
| `region` | `id`, `key`, `name`, `postal_codes text[]` | GIN-Index auf `postal_codes` |
| `event` | Felder laut Datenmodell, dazu `location geography(Point,4326)`, `postal_code`, `search_text` (generiert, `unaccent(lower(...))`), `version`, `source`, `source_url`, `ai_job_id`, `favorite_count`, Audit, `deleted_at` | GiST auf `location`, GIN-trgm auf `search_text`, Index `(status, end_date)` |
| `program_item` | `id`, `event_id`, `date`, `time_label`, `title`, `subtitle`, `position` | |
| `event_image` | `id`, `event_id`, `object_key`, `thumb_key`, `position`, `width`, `height`, `status` | befüllt ab R08 |

Domain: `Event` als Aggregat mit `ProgramItem`, Value Objects `DateRange`, `GeoPoint`, `PostalCode`, `CategoryColor` (Palette). Die Regeln „sichtbar“, „läuft“ und „vergangen“ sind Domain-Funktionen mit einer injizierten Uhr (`Clock`-Port) für Tests.

## Tests

- Unit: Zeitraum-Semantik (today, weekend inkl. Sonntag, Monatsüberschneidung, Jahreswechsel), Sichtbarkeit, Sortierung, laufend/vergangen an den Tagesgrenzen in `Europe/Berlin` (auch Sommerzeitwechsel).
- Integration (Testcontainers PostGIS/Redis): Radius- und bbox-Suche, Trigram-Suche („Reichstaedter“ findet „Reichsstädter Tage“), `byCategory`-Zählung, Cache-Hit/-Invalidierung über die Generation, Nominatim-Adapter gegen aufgezeichnete Antworten (kein Live-Aufruf).
- Contract: Schemathesis für alle öffentlichen Endpunkte.
- Performance-Stichprobe: 10.000 Feste, Radius 150 km → p95 < 150 ms ohne Cache (lokal gemessen, dokumentiert).

## Doku/Betrieb

- `40-operations/nominatim.md`: Import Deutschland (Geofabrik), Ressourcenbedarf, Update-Strategie (Replication), Prüfung und Rollback.
- VVT: Geocoding-Anfragen (Ortsnamen, Koordinaten) werden nur verarbeitet, nicht gespeichert. Eingetragen wird die Verarbeitung „Suche“ mit Standortdaten.

## Definition of Done

- [ ] Alle Endpunkte stehen in `openapi.yaml`, sind generiert und durch Contract-Tests abgedeckt.
- [ ] `make seed` liefert Daten, die in der Detail- und Suchantwort sichtbar sind.
- [ ] Ein Test zeigt, dass Logs keine Koordinaten, `q`-Werte und IPs enthalten.
- [ ] Nominatim-Runbook und ADR (aus R01) sind aktuell.

## Offene Punkte

- Sollen abgesagte Feste im Karussell nach hinten sortiert werden? Vorerst nicht, sie behalten ihre Position mit dem Status „Abgesagt“.
