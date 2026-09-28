# 0006 · Selbst gehostetes Nominatim für Geocoding

- **Status:** angenommen
- **Datum:** 2026-09-28
- **Bezug:** E-05, E-10, E-11

## Kontext

Die App braucht mehrere Geocoding-Funktionen:
- PLZ- und Ortssuche mit Vorschlägen (Wohnort, KI-Suche)
- Straßenadressen (Moderation)
- Reverse-Geocoding von Nutzerpositionen

Die Usage Policy des öffentlichen OSM-Nominatim verbietet Autocomplete und erlaubt nur 1 Anfrage/s. Nutzerpositionen sind personenbezogene Daten und sollen die eigene Infrastruktur nicht verlassen.

## Entscheidung

- **Nominatim wird selbst gehostet** als Container im Produktionsstack auf dem Heimserver (EU). Importiert wird der Geofabrik-Extrakt für Deutschland mit regelmäßigen Updates.
- Es gibt **keine eigene PLZ-Tabelle**. Eine Region ist eine Liste von PLZ (E-05). Die Zugehörigkeit eines Fests ergibt sich aus seiner PLZ.
- Die App ruft Nominatim **nie direkt** auf, sondern nur über `/v1/geocode*`. Das Backend nutzt einen Geocoding-Port mit Redis-Cache (30 Tage).
- **Lokal:** Standard ist ein Fake-Adapter. Optional läuft ein Nominatim-Container mit Regionsextrakt (Compose-Profil `geo`).
- **Tests:** nie ein Live-Nominatim, stattdessen aufgezeichnete Antworten.

## Konsequenzen

- Betriebsaufwand: grob 8–16 GB RAM, 100+ GB SSD, mehrstündiger Initialimport. Das Runbook `40-operations/nominatim.md` folgt in R02.
- Keine Weitergabe von Nutzerpositionen an Dritte.

## Verworfene Alternativen

- Öffentliches Nominatim: kein Autocomplete, Limit, Nutzerdaten an Dritte.
- Eigene PLZ-Tabelle: zusätzliche Datenpflege, auf Wunsch des Product Owners verworfen.
