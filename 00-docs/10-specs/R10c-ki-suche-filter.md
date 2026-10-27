# R10c · Feinere KI-Suche und mehr Felder

| | |
|---|---|
| **Ziel** | Moderierende können die KI-Suche optional eingrenzen (Zeitraum, Kategorien, Umkreis, Suchschwerpunkte). Die KI liest zusätzlich Website, Uhrzeiten je Tag und Eintritt aus. Die Postleitzahl bleibt die einzige Pflichtangabe. |
| **Hängt ab von** | R10, R10b, R15 |
| **Quellen** | Analyse „KI-Suche erweitern“ vom 27.10.2026, Entscheidungen von Lukas vom selben Tag (Bildvorschlag mit Bestätigung, Suchschwerpunkte statt Freitext, Uhrzeiten als `openingHours`, MCP-Tool mit Filtern) |
| **Bounded Context** | `ai_ingestion` |
| **Rollen** | Moderator |

**Nicht drin** (folgende Inkremente): strukturierte Daten (JSON-LD, iCal) vor dem Modell auswerten, Bildvorschlag mit Bestätigung im Prüfmodus, nächsten Termin eines bekannten Fests suchen, Kalender-URL direkt einlesen.

## User Stories

### R10c-US1 · Optionale Filter im Sheet
- Unter dem PLZ-Feld liegt ein zugeklapptes Akkordeon „Weitere Filter (optional)“ (`mod.ai.filters`). Zugeklappt zeigt es „Standard: 12 Monate, alle Kategorien, 25 km“, mit Filtern „{n} Filter aktiv“.
- Aufgeklappt:
  - **Zeitraum:** „Von“ und „Bis“ (Datumsfelder). Beginn frühestens heute, Ende nicht vor dem Beginn, höchstens 365 Tage im Voraus. Fehler stehen unter den Feldern; „Suche starten“ ist dann gesperrt.
  - **Kategorien:** Chips der aktiven Kategorien, Mehrfachauswahl. Keine Auswahl = alle.
  - **Umkreis:** Chips 10 / 25 / 50 km, Einfachauswahl. Keine Auswahl = `AI_SEARCH_RADIUS_KM`.
  - **Suchschwerpunkte:** Chips „Auch kleine Dorffeste“, „Nur große Feste“, „Gemeindekalender zuerst“, „Zeitungen und Amtsblätter“. „Auch kleine Dorffeste“ und „Nur große Feste“ schließen sich aus.
  - „Filter zurücksetzen“, sobald ein Filter gesetzt ist.
- Ohne Filter sendet die App den Request wie bisher (`{postalCode}`).

### R10c-US2 · API und Job
- `POST /v1/mod/ai-searches {postalCode, filters?}` mit `filters = {dateFrom?, dateTo?, categoryIds?, radiusKm?, focus?}` (`AiSearchFilters`, keine weiteren Felder erlaubt).
- Prüfung im Use Case (gilt für REST und MCP): `422 validation_failed` mit `fields`:
  - `dateFrom: past`
  - `dateTo: before_start | too_far`
  - `categoryIds: unknown | too_many` (nur aktive Kategorien, höchstens 20)
  - `radiusKm: invalid` (5 bis 50)
- Doppelte Kategorien und Schwerpunkte werden entfernt. Der Job speichert die Filter (Migration 0014, Spalten `filter_*`), `AiSearch.filters` gibt sie zurück.
- Neuer Zähler `skipped.notMatching`: Funde außerhalb des Zeitraums oder sicher einer anderen Kategorie zugeordnet.

### R10c-US3 · Pipeline mit Filtern
- Zeitraum des Laufs: Beginn = gewählter Beginn, aber nie vor heute (der Job kann in der Queue über Mitternacht warten); Ende = gewähltes Ende oder heute + 365 Tage.
- Der Prompt nennt nur die gewählten Kategorien, den gewählten Umkreis und die Textbausteine der Suchschwerpunkte (`{focus}`). Orte im Umkreis und die Umkreisprüfung nutzen den gewählten Radius.
- Funde, die den Zeitraum nicht berühren, zählen als `notMatching`.
- Kategorie: Nur ein Fund, der **sicher** einer anderen Kategorie zugeordnet wird, zählt als `notMatching`. Ohne sichere Zuordnung bleibt er (die Zuordnung per Synonymliste ist zu unscharf zum Verwerfen).

### R10c-US4 · Mehr Felder (Schema `EventDraftV2`)
- Neue optionale Felder: `website_url`, `opening_hours` (Liste `{day, opens, closes}`, Uhrzeit `SS:MM`, Ortszeit Berlin) und `price`.
- Ein kaputter Wert verwirft nur das Feld, nicht den Fund.
- **Website:** Bleibt nur, wenn sie in den Suchergebnissen des Jobs oder in den Links einer gelesenen Seite steht und erreichbar ist. Sonst wird das Feld geleert. `read_page` liefert dazu bis zu 40 Links außerhalb der Navigation („Links auf der Seite:“).
- **Uhrzeiten:** werden zu `openingHours`-Zeilen wie „Fr 12.06. 18-24 Uhr“ oder „Sa 13.06. ab 11 Uhr“, nur für Tage innerhalb des Festzeitraums, höchstens 10. Keine Änderung am Fest-Datenmodell.
- **Eintritt:** kurzer Text, höchstens 200 Zeichen, in `price`.
- Der Prüfmodus zeigt zusätzlich die Website.

### R10c-US5 · Prompt v4
- v3 plus Anleitung für Website, Uhrzeiten, Eintritt und die Zeile „Suchschwerpunkte: …“. Neuer erlaubter Platzhalter `focus`.
- `AI_SEARCH_PROMPT_VERSION` Standard `v4`. v1 bis v3 bleiben unverändert.
- Vor dem Einsatz in Produktion `make ai-eval ZIPS="73430 73525" PROMPTS=v3,v4` mit echten Anbietern laufen lassen (kostet Anfragen, nie in der CI).

### R10c-US6 · MCP-Tool
- `start_ai_search(zip_code, date_from?, date_to?, categories?, radius_km?, focus?)`. Kategorien als Namen (ohne Groß-/Kleinschreibung), unbekannte Namen ergeben einen Tool-Fehler mit den erlaubten Namen. Dieselbe Prüfung wie REST im Use Case.

## Datenschutz

- Es gibt **keinen Freitext**. Moderierende wählen nur aus festen Werten. Die Textbausteine der Suchschwerpunkte stehen im Code (`FOCUS_HINTS`) und enthalten keine Personendaten.
- Neue Daten im Job (`filter_*`) sind Zeitraum, Kategorie-IDs, Radius und Schwerpunkt-Schlüssel, kein Personenbezug. Sie bleiben wie die Job-Zeile erhalten.
- An LLM und Suche gehen weiterhin nur PLZ, Ortsnamen, Radius, Zeitraum, Kategorienamen und die festen Textbausteine.
- Links gelesener Seiten sind öffentliche Seiteninhalte; das Job-Protokoll speichert sie nicht.

## Tests

- Domain: v4 ohne offene Platzhalter, jeder Schwerpunkt hat einen Text, Uhrzeiten streng geparst, `openingHours`-Zeilen, Überschneidung mit dem Zeitraum.
- Use Case: Filter werden geprüft und gespeichert, Prompt mit und ohne Filter, `notMatching` für Zeitraum und Kategorie, Radius-Filter, Website aus Seitenlinks, erfundene und tote Websites werden geleert.
- REST: Filter im Request und in der Antwort, Feldfehler, Zusatzfelder (z. B. `prompt`) werden abgelehnt.
- MCP: Filter mit Kategorienamen, unbekannte Kategorie, freie Schwerpunkte und Zusatzfelder werden abgelehnt.
- Integration (PostGIS): Filter-Rundreise, `notMatching`, Website/Uhrzeiten/Eintritt im Entwurf.
- Seitenleser: Links außerhalb der Navigation, absolute URLs, ohne Fragmente und Dubletten.
- App: Akkordeon zugeklappt, Filter wählen und senden, Schwerpunkte schließen sich aus, Zeitraumprüfung, Story und Test für `Accordion`.

## Definition of Done

- [ ] `make check` grün
- [ ] `make ai-eval` mit echten Anbietern (v3 gegen v4) lokal ausgeführt
- [ ] `AI_SEARCH_PROMPT_VERSION=v4` im Stack `stadtfest` des HomeLab gesetzt (oder Zeile entfernt)
