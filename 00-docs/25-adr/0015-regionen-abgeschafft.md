# 0015 · Moderationsregionen abgeschafft

- **Status:** angenommen
- **Datum:** 2026-10-05
- **Ersetzt:** Entscheidung E-05 (Region als Menge von PLZ); die Abschnitte zur Region in ADR 0003 und ADR 0006

## Kontext

Bisher war jeder Moderator an eine Region gebunden, eine feste Menge von Postleitzahlen (E-05):
- Die Region kam als Claim `region` aus dem Token. Ohne Region gab es keine Moderationsrechte.
- Moderatoren sahen und pflegten nur Feste ihrer Region; Feste anderer Regionen antworteten mit `404`.
- Die KI-Suche (R10) erlaubte nur PLZ der eigenen Region und verwarf Funde außerhalb.

Im ersten echten Test der KI-Suche (05.10.2026) zeigte sich, dass das nicht passt:
- Die Regionen decken nur wenige PLZ ab.
- Feste am Rand einer Region fielen weg.
- Jede neue Gegend brauchte zuerst eine gepflegte PLZ-Liste und Moderatoren mit passendem Claim.

Der Projektinhaber hat entschieden, Regionen ganz abzuschaffen.

## Entscheidung

- **Keine Regionen mehr.** Die Rolle `moderator` allein berechtigt, **alle** Feste in Deutschland anzulegen, zu bearbeiten, zu veröffentlichen, abzusagen und zu löschen, einschließlich ihrer Bilder. Die Prüfungen bleiben in den Use Cases; es entfällt nur der Regionsvergleich.
- **KI-Suche für jede PLZ:**
  - Jeder Moderator darf jede in Deutschland bekannte PLZ durchsuchen. Eine unbekannte PLZ ergibt `422 postal_code_unknown`.
  - Gesucht wird im Umkreis `AI_SEARCH_RADIUS_KM` um den Mittelpunkt der PLZ.
  - Funde außerhalb dieses Umkreises (plus 10 % Toleranz) oder ohne bestimmbaren Ort werden übersprungen und gezählt (`skipped.outOfArea`).
- **Duplikate und verworfene Quellen** gelten bundesweit:
  - Ein Fund ist ein Duplikat, wenn ein Fest mit ähnlichem Namen, überlappendem Zeitraum und < 2 km Abstand existiert oder seine Quelle schon vorhanden ist.
  - Eine verworfene Quelle wird nirgends mehr vorgeschlagen.
- **Daten:**
  - Die Tabelle `region` und die Spalte `event.region_id` entfallen (Migration 0008).
  - `ai_search_job` und `rejected_source` haben keine Regionsspalte mehr.
- **IdP:**
  - Kein Claim `region` mehr; `AUTH_REGION_CLAIM` entfällt.
  - Ein vorhandenes Region-Metadatum beim IdP wird ignoriert und kann gelöscht werden.
- **API v1 wird bewusst inkompatibel geändert**, ohne neue Version:
  - `ModEventDetail.regionId`, `Me.region` und das Schema `RegionRef` entfallen.
  - Die Fehlercodes `region_mismatch` und `postal_code_outside_region` entfallen; dafür kommt `postal_code_unknown`.
  - `AiSearchSkipped.outOfRegion` heißt jetzt `outOfArea`.

  Begründung: Es gibt noch keine veröffentlichte App und keine fremden Clients. Die eigene App wird im selben PR angepasst. Der CI-Check `oasdiff` bekommt dafür eine einmalige, dokumentierte Ausnahmeliste (`api/oasdiff-err-ignore.txt`). Nach dem ersten Release gilt wieder: inkompatible Änderungen nur mit neuer API-Version.

## Datenschutz

Weniger Daten:
- Das Region-Metadatum der Moderatoren beim IdP und der Region-Claim im Token entfallen.
- Moderator-Nutzer-IDs in Prüf- und Audit-Feldern bleiben unverändert.
- Der Prompt der KI-Suche enthält wie bisher nur PLZ, Ortsname, Radius, Zeitraum und Kategorien.

## Konsequenzen

- Jede Moderatorin und jeder Moderator kann überall Feste pflegen. Missbrauch wird nur organisatorisch begrenzt: durch die Vergabe der Rolle und die Audit-Felder `created_by`/`updated_by`. Das ist bei einem kleinen, bekannten Moderationsteam vertretbar.
- Die Moderationsübersicht zeigt alle Feste in Deutschland. Suche (`q`) und Statusfilter bleiben; bei großem Bestand sind später Paginierung oder ein Umkreisfilter nötig.
- Die Einrichtung neuer Moderatoren wird einfacher: nur noch die Rolle, keine Region (Runbook [moderator-einrichten.md](../40-operations/moderator-einrichten.md)).
- Der Umkreis der KI-Suche hängt am Geocoding. Lokal mit `GEOCODING_PROVIDER=fake` lassen sich nur Orte rund um Aalen auflösen; für echte Läufe braucht es Nominatim.

## Verworfene Alternativen

- **Nur die KI-Suche öffnen, Pflege regional lassen:** Funde außerhalb der eigenen Region hätte niemand prüfen können, oder es hätte Sonderrechte für den Suchenden gebraucht.
- **Neue API-Version `/v2`:** regelkonform, aber vor dem ersten Release reiner Mehraufwand ohne Nutzen.
