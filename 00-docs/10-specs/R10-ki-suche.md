# R10 · KI-Suche per PLZ

| | |
|---|---|
| **Ziel** | Ein Moderator stößt per Postleitzahl eine asynchrone Suche an. Ein Worker sucht mit einem LLM und einem Web-Such-Tool nach Veranstaltungen, validiert die Funde und legt sie als **Entwurf** an. Der Moderator prüft die Funde anschließend Stück für Stück. |
| **Hängt ab von** | R07 (Formular, Veröffentlichen, Outbox). R08/R09 sind nicht nötig. |
| **Quellen** | [09 KI-Suche](../15-design/workflows/09-moderation-ki-suche.md), [CLAUDE.md „AI ingestion“](../../CLAUDE.md), Architektur Flow C1–C8, Screens 09-01 bis 09-05. Entscheidung E-12. |
| **Bounded Context** | `ai_ingestion` (Job, Entwurfsschema), `moderation` (Prüfen) |
| **Rollen** | Moderator |

## Umfang

**Drin:**
- Job-Modell und Endpunkte
- LLM-Port mit **einem generischen Adapter**, Web-Such-Port mit Anbieter-Adapter, beide mit Fake-Adapter
- Worker-Pipeline: Geocoding → LLM mit Tool → Validierung → Quellenprüfung → Regionsprüfung → Duplikatabgleich → Entwürfe
- Job-Protokoll, Rate-Limit
- App: PLZ-Sheet, Statusleiste mit Polling, Prüfmodus

**Nicht drin:**
- Push beim Abschluss (R11)
- MCP-Tool `start_ai_search` (R15)
- Übernahme von Bildern aus Quellen

## User Stories

### R10-US1 · Suche starten
- „Suchen“ in der Übersicht → Sheet „Feste automatisch suchen“ (09-01) mit Erklärung und PLZ-Feld: nur Ziffern, genau 5, Schrift 22/600, Laufweite .12em.
- Bei 5 Ziffern zeigt die App den Ort über `GET /v1/geocode?q={plz}` an. Unbekannte PLZ: „Diese Postleitzahl kennen wir nicht.“
- „Suche starten“ ist nur bei gültiger Eingabe aktiv. Fehlertext: „Bitte gib eine fünfstellige Postleitzahl ein.“
- `POST /v1/mod/ai-searches {postalCode}` → `202 {jobId, status: queued}`:
  - `422 postal_code_outside_region`, wenn die PLZ nicht zur Region des Moderators gehört (Annahme)
  - `409 {jobId}`, wenn bereits ein Job des Moderators `queued|running` ist
  - `429`, wenn das Tageslimit erreicht ist (`AI_SEARCH_DAILY_LIMIT`, Standard 10 pro Moderator)
- Der Request kehrt sofort zurück. Die Arbeit läuft im Worker (Enqueue über die Outbox: `ai_search.requested`).

### R10-US2 · Status verfolgen
- Leiste in `modSoft` mit Spinner: „Suche läuft für {PLZ} {Ort} …“ (09-02). Die Übersicht bleibt bedienbar.
- `GET /v1/mod/ai-searches/{jobId}` alle 10 s, solange die Leiste sichtbar ist. `GET /v1/mod/ai-searches?status=running` beim Öffnen der Moderationsansicht stellt die Leiste nach einem App-Neustart wieder her.
- **Abschluss (09-03):**
  - Leiste „{n} neue Entwürfe aus der Suche für {PLZ}“ mit „Prüfen“ und ✕, Toast
  - Funde erscheinen in der Übersicht als Entwurf mit der Pill „Automatisch gefunden“
  - Bei `n = 0`: „Keine neuen Feste für {PLZ} gefunden“ plus Anzahl übersprungener Duplikate (Annahme)
- **Fehlgeschlagen:** Leiste „Suche fehlgeschlagen · Erneut versuchen“. Erneut versuchen startet einen neuen Job (Annahme, nicht gestaltet).
- Job-Antwort: `{id, postalCode, placeName, status, startedAt, finishedAt, newEventIds[], skipped: {duplicate, outOfRegion, invalid, unverifiedSource}, errorCode?}`.

### R10-US3 · Worker-Pipeline
1. **Geocoding:** PLZ → Mittelpunkt über den Geocoding-Port. Der Suchradius ist `AI_SEARCH_RADIUS_KM` (Standard 25).
2. **Prompt**, nur mit erlaubten Parametern (CLAUDE.md, Datenschutz):
   - PLZ, Ortsname, Radius
   - Zeitraum heute bis heute + 12 Monate
   - Namen der aktiven Kategorien
   
   **Keine** Moderator-Daten, keine Region-IDs, keine Nutzerdaten.
3. **LLM mit Web-Such-Tool:** Das Tool ist providerunabhängig definiert und wird vom LLM aufgerufen.
   - Grenzen: `AI_SEARCH_MAX_TOOL_CALLS` (Standard 8), `AI_SEARCH_TIMEOUT_S` (Standard 300), max. Ausgabetokens.
   - Alle vom Tool gelieferten URLs merkt sich der Job.
4. **Strukturierte Ausgabe** nach dem festen, versionierten Schema `EventDraftV1`: `name`, `date_from`, `date_to`, `place`, `address`, `coordinates?`, `category?`, `source_url`, `description?`.
5. **Validierung mit Pydantic:** Ungültige Einträge werden verworfen und nur **als Anzahl** protokolliert, ohne Inhalt. `date_to ≥ date_from`, Datum nicht in der Vergangenheit.
6. **Quellenprüfung:**
   - `source_url` ist Pflicht, `http(s)`, und muss **unter den URLs sein, die das Such-Tool in diesem Job geliefert hat** (Schutz gegen erfundene Quellen)
   - Die Seite muss per HEAD/GET erreichbar sein (Status < 400, Timeout 5 s)
   - Sonst zählt der Eintrag zu `unverifiedSource`
7. **Ort:** Fehlen Koordinaten oder sind sie unplausibel, wird die Adresse über Nominatim geocodiert. Die PLZ muss in der Region liegen, sonst `outOfRegion`.
8. **Kategorie:** Der Name wird auf eine aktive Kategorie gemappt (exakt bzw. Synonyme). Ohne sichere Zuordnung bleibt sie leer.
9. **Duplikate:** Abgleich gegen bestehende Feste der Region (alle Status außer gelöscht) und gegen **verworfene Quellen**:
   - Treffer, wenn Namensähnlichkeit (trgm) ≥ 0,5, Zeiträume sich überschneiden und die Entfernung < 2 km beträgt, oder wenn die normalisierte `source_url` bereits vorhanden bzw. verworfen ist
   - Bestehende Feste werden **nicht überschrieben**
10. **Entwürfe anlegen:** `status=draft`, `source=ai`, `sourceUrl`, `aiJobId`, `foundAt`, `regionId`. Kein direktes Veröffentlichen, niemals.
11. Job auf `completed` bzw. `failed` (mit `errorCode`: `llm_unavailable`, `search_unavailable`, `timeout`, `internal`) setzen. Event `ai_search.completed|failed` in die Outbox.

- Job-Status: `queued → running → completed | failed`. Hängende Jobs (Worker-Absturz) setzt ein Wächter-Job nach `2 × AI_SEARCH_TIMEOUT_S` auf `failed`.
- **Protokoll pro Job:** Suchanfragen des Tools, gelieferte Quellen-URLs, Zähler, Dauer, Token-Verbrauch. Keine Nutzerdaten. Nach 90 Tagen kürzt ein wöchentlicher Job das Protokoll auf die Zähler.

### R10-US4 · Funde prüfen
- „Prüfen“ → `GET /v1/mod/events?ids=…` → Prüfmodus (09-04):
  - oben ein Fortschritt aus Segmenten (Türkis = erledigt, Rosa = verworfen)
  - je Fund: Bild bzw. „Kein Bild gefunden“, Name, Kategorie, Zeitraum, Adresse
  - Kasten „Gefunden auf {Domain}“ mit „Öffnen ↗“
  - Tabelle der Angaben, fehlende in Rosa als „fehlt“
- **Veröffentlichen:** nur bei vollständigen Pflichtfeldern (`POST …/publish`), sonst öffnet sich das Formular mit Hinweis. Danach der nächste Fund.
- **Bearbeiten:** Formular aus R07. Nach dem Speichern der nächste Fund.
- **Verwerfen:** `DELETE /v1/mod/events/{id}`, die normalisierte `sourceUrl` kommt in `rejected_source` (pro Region). Toast „Verworfen“, nächster Fund.
- **✕ pausiert:** Toast „Pausiert · offene Funde bleiben als Entwurf“. Die Leiste mit „Prüfen“ bleibt.
- **Ende (09-05):** „Alle Funde geprüft“, Zusammenfassung (n veröffentlicht, n bearbeitet, n verworfen), „Zur Übersicht“. Die Leiste verschwindet.

## Konfiguration (`.env.example`, Validierung beim Start)

```bash
LLM_PROVIDER=mistral          # mistral | openai | anthropic | ollama | fake
LLM_MODEL=mistral-large-latest
LLM_API_KEY=                  # nicht nötig für ollama/fake
LLM_BASE_URL=
WEB_SEARCH_PROVIDER=...       # per ADR festgelegt | fake
WEB_SEARCH_API_KEY=
AI_SEARCH_RADIUS_KM=25
AI_SEARCH_DAILY_LIMIT=10
AI_SEARCH_MAX_TOOL_CALLS=8
AI_SEARCH_TIMEOUT_S=300
```

Unbekannter Anbieter oder fehlender Schlüssel beenden den Start (fail fast). `fake` ist nur mit `ENV=dev|test` erlaubt.

## Daten

- `ai_search_job`: Felder laut Datenmodell + `place_name`, `skipped_*`-Zähler, `error_code`, `log jsonb`, `token_usage`.
- `rejected_source`: `region_id`, `url_normalized`, `rejected_at`.
- `event`: `found_at`.

## Datenschutz

- Die Prompt-Erzeugung ist eine reine Funktion mit Test: Der Prompt enthält nur die erlaubten Felder (Snapshot-Test).
- LLM- und Such-Anbieter sind ggf. Nicht-EU-Verarbeiter → ADR mit Rechtsgrundlage. Standard in Produktion: Mistral (EU) oder Ollama. Es gehen keine personenbezogenen Daten an Anbieter.
- Protokolle ohne Nutzerdaten, Löschfrist 90 Tage.
- `DeleteAccount`: `moderator_id` in Jobs wird auf `null` gesetzt.

## Tests

- **Nie echte Anbieter in Tests.** Es gibt Fake-LLM und Fake-Suche sowie aufgezeichnete Fixtures (echte, anonymisierte Antworten) für den generischen Adapter.
- Unit:
  - Prompt-Snapshot
  - Validierung (ungültige Einträge verworfen und gezählt)
  - Quellenprüfung: URL nicht aus dem Tool → abgelehnt
  - Duplikaterkennung inkl. verworfener Quellen
  - Kategorie-Mapping
  - Region `409`/`429`/`422`
  - Wächter für hängende Jobs
- Integration: kompletter Job mit Fakes gegen PostGIS/Redis (Entwürfe angelegt, Zähler korrekt), Erreichbarkeitsprüfung gegen einen lokalen HTTP-Stub.
- Contract: Job-Endpunkte (`202`, `409`).
- RNTL: PLZ-Sheet, Statusleiste (laufend, fertig, fehlgeschlagen, Wiederherstellung), Prüfmodus.
- Maestro: Moderator startet die Suche (Fake-Anbieter liefert 3 Funde) → Prüfen → veröffentlicht 1, bearbeitet 1, verwirft 1 → Zusammenfassung.

## Doku/Betrieb

- **ADR:** generischer LLM-Adapter (LiteLLM vs. Pydantic AI), Anbieterwahl per ENV.
- **ADR:** Web-Such-Anbieter (EU bevorzugt), ggf. Nicht-EU-Verarbeiter mit Rechtsgrundlage.
- **ADR:** Nicht-EU-LLM-Anbieter (OpenAI, Anthropic) als optionale Verarbeiter.
- `40-operations/llm-anbieter.md` und `40-operations/web-suche.md`: Schlüssel anlegen, Limits und Kosten, Umschalten per ENV, Prüfung.
- Architektur: Flow C in `system-architecture.md` prüfen und aktualisieren.

## Definition of Done

- [ ] Screens 09-01 bis 09-05 umgesetzt, dunkel und hell.
- [ ] Der Wechsel des LLM-Anbieters erfordert nur ENV-Änderungen. Das zeigt ein Test, der die Adapter-Konfiguration für alle vier Anbieter baut.
- [ ] Kein Entwurf ohne verifizierte `source_url` (Test).
- [ ] ADRs und Runbooks liegen vor.

## Offene Punkte

- Änderungsvorschläge für bestehende Feste (z. B. neue Öffnungszeiten)? Vorerst werden sie übersprungen.
- Kostenlimit pro Monat und Region zusätzlich zum Tageslimit?
