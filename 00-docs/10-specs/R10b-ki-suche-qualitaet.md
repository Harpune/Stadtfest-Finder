# R10b · Bessere Treffer der KI-Suche

| | |
|---|---|
| **Ziel** | Die KI-Suche findet mehr und belastbarere Feste. Grundlage sind die ersten echten Läufe am 05.10.2026: Die Modelle schrieben Radius und ISO-Daten in die Suchanfragen („Stadtfest Ulm und Umgebung 25 km 2026-10-05 bis 2027-10-05“), sahen nur Snippets und lieferten aus rund 40 Quellen 3 Funde. |
| **Hängt ab von** | R10, [ADR 0015](../25-adr/0015-regionen-abgeschafft.md) |
| **Bounded Context** | `ai_ingestion` |
| **Rollen** | Moderator (keine sichtbare Änderung in der App) |

## User Stories

### R10b-US1 · Prompt v2 mit Suchregeln
- Kurze Suchanfragen wie von Menschen („Stadtfest Ellwangen 2026/2027“, „Veranstaltungskalender Aalen“), keine Kilometer, PLZ-Bereiche oder ISO-Daten in Anfragen.
- Ort für Ort suchen, zuerst Veranstaltungskalender der Städte und Gemeinden, dann gezielt je Kategorie.
- Offizielle Quellen bevorzugen (Städte, Gemeinden, Tourismusämter, Veranstalter, regionale Zeitungen); Ticketshops, soziale Netzwerke und überregionale Portale nur ersatzweise.
- Kalender- und Übersichtsseiten: jedes passende Fest einzeln zurückgeben.
- Ausschluss: Dauerausstellungen, Kurse, Einzelkonzerte, Sport, private Feiern.

### R10b-US2 · Orte im Umkreis
- Der Worker bestimmt die Orte im Suchumkreis per Reverse-Geocoding: Mittelpunkt der PLZ, 6 Punkte bei 45 % und 10 Punkte bei 85 % des Radius.
- Die Ortsnamen werden ohne Dubletten und nach Nähe sortiert (der gesuchte Ort zuerst, höchstens 12) als `{nearby_places}` in den Prompt gegeben.
- Fällt das Geocoding für einzelne Punkte aus, wird die Liste nur kürzer.
- Ortsnamen sind öffentliche Daten. Sie stehen im Job-Protokoll (`nearbyPlaces`) und werden nach 90 Tagen mit den Suchanfragen gekürzt.

### R10b-US3 · Prompt-Versionen
- Prompts sind Dateien im Code: `backend/src/stadtfest/application/ai_ingestion/prompts/v1.md`, `v2.md` usw. Teile: `<!-- system -->` und `<!-- user -->`.
- Platzhalter nur aus der Erlaubnisliste: `postal_code`, `place_name`, `radius_km`, `date_from`, `date_to`, `years`, `categories`, `nearby_places`. Andere Platzhalter beenden den Start (Schutz vor personenbezogenen Daten im Prompt).
- Auswahl: `AI_SEARCH_PROMPT_VERSION` (Standard `v2`). Für Experimente lokal `AI_SEARCH_PROMPT_FILE` (in `prod` abgelehnt).
- `v1` bleibt unverändert (Snapshot-Test), damit Vergleiche möglich sind.
- Das Job-Protokoll speichert die Version (`prompt`); sie bleibt auch nach dem Kürzen erhalten.

### R10b-US4 · Auswertung
- `make ai-eval ZIPS="73430 89073" PROMPTS=v1,v2 [OUT=bericht.md]` führt die echte Pipeline mit den konfigurierten Anbietern aus.
  - Jobs bleiben im Speicher, es werden keine Entwürfe gespeichert. Die Duplikatprüfung läuft gegen die lokale Datenbank.
  - Der Bericht in Markdown enthält je PLZ und Version: Status, neue Funde, Übersprungene je Grund, Anzahl Suchen, Tokens, Dauer, Orte im Umkreis, Suchanfragen und Funde mit Quelle.
- Nie in der CI: Jeder Lauf kostet Anfragen bei LLM und Suchmaschinen.

### R10b-US5 · Seiten lesen (folgt)
- Zweites Werkzeug `read_page(url)`: Das Modell liest den Text eines Suchtreffers. Erlaubt sind nur URLs aus den Suchergebnissen desselben Jobs, mit SSRF-Schutz und Längenbegrenzung.

## Datenschutz

Im Prompt kommen nur öffentliche Ortsnamen aus dem Geocoding hinzu. Weiterhin keine Nutzer- oder Moderatordaten. Die Erlaubnisliste der Platzhalter erzwingt das technisch.

## Tests

- Domain:
  - v1 unverändert (Snapshot);
  - v2 enthält Orte und Jahre und keine offenen Platzhalter;
  - unbekannte Platzhalter werden abgelehnt;
  - Dateiformat;
  - Geometrie `destination`.
- Use Case: Orte im Umkreis (Dubletten, Reihenfolge, Anzahl Abfragen), Version im Protokoll, Version aus den Einstellungen.
- Einstellungen: unbekannte Version, ungültige Datei, Datei in `prod`.
- `ai_eval` mit Fakes: nichts gespeichert, Bericht je Version.

## Definition of Done

- [ ] `make check` grün
- [ ] `make ai-eval` mit echten Anbietern lokal ausgeführt, Ergebnis im PR
