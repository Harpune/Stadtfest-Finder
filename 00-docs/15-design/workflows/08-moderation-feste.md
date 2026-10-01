# 08 · Moderation: Feste

| | |
|---|---|
| **Ziel** | Moderatoren pflegen die Feste ihrer Region: anlegen, bearbeiten, als Entwurf speichern, veröffentlichen, absagen und löschen. |
| **Rollen** | Moderator (nur Feste der eigenen Region) |
| **Moderationsansicht** | **Ja.** Türkis statt Amber als Akzent, festes Banner „MODERATOR-ANSICHT · Region Ostalb · Name“ mit „Beenden“ und eine eigene Tab-Leiste „Feste / Kategorien“. |
| **Einstieg** | Profil-Drawer → „Moderator-Ansicht“ ([04](04-favoriten-und-zeitleiste.md)) |
| **Weiter zu** | [09 KI-Suche](09-moderation-ki-suche.md), [10 Kategorien](10-moderation-kategorien.md) |
| **Wirkt auf** | [01](01-stadtfest-suche.md) und [02](02-fest-details.md) (sichtbare Feste), [07](07-benachrichtigungen.md) (Benachrichtigungen) |

## Screens

| Feste der Region | Bearbeiten: oben | Bearbeiten: Ort | Bearbeiten: Programm, Bilder |
|---|---|---|---|
| <img src="../screenshots/08-01-mod-feste.png" width="200"> | <img src="../screenshots/08-02-mod-fest-bearbeiten.png" width="200"> | <img src="../screenshots/08-03-mod-fest-ort.png" width="200"> | <img src="../screenshots/08-04-mod-fest-programm-bilder.png" width="200"> |
| **Neues Fest** | **Validierung** | **Ort per Pin** | **Menü ⋯** |
| <img src="../screenshots/08-05-mod-fest-neu.png" width="200"> | <img src="../screenshots/08-06-mod-fest-validierung.png" width="200"> | <img src="../screenshots/08-07-mod-fest-pin.png" width="200"> | <img src="../screenshots/08-08-mod-fest-menue.png" width="200"> |
| **Absagen** | **Löschen** | **Hellmodus** | |
| <img src="../screenshots/08-09-mod-fest-absagen.png" width="200"> | <img src="../screenshots/08-10-mod-fest-loeschen.png" width="200"> | <img src="../screenshots/08-11-mod-feste-hell.png" width="200"> | |

## Statusmodell

```mermaid
stateDiagram-v2
  [*] --> Entwurf: anlegen / KI-Fund
  Entwurf --> Veröffentlicht: veröffentlichen (Pflichtfelder)
  Veröffentlicht --> Entwurf: „Als Entwurf“ (zurückziehen)
  Veröffentlicht --> Abgesagt: absagen (+ Benachrichtigung)
  Veröffentlicht --> Vergangen: Ende < heute (automatisch, abgeleitet)
  Abgesagt --> Vergangen: Ende < heute
  Entwurf --> [*]: löschen
  Veröffentlicht --> [*]: löschen
  Abgesagt --> [*]: löschen
```

| Status | In der App sichtbar | Bearbeitbar |
|---|---|---|
| Entwurf | nein | ja |
| Veröffentlicht | ja | ja; Änderungen an Datum, Zeiten oder Ort lösen „Änderung“ aus |
| Abgesagt | ja, mit Status „Abgesagt“ | ja (nur Texte; Wiederaufnahme nicht vorgesehen) |
| Vergangen | nein in Karte und Liste, ja in Zeitleiste und Listen | ja (für Korrekturen) |

## Ablauf

```mermaid
flowchart TD
  DR([04 Drawer · Moderator-Ansicht]) --> O[Übersicht · GET /v1/mod/events]
  O -->|Suche / Status-Chip| O
  O -->|„+ Neues Fest“| F[Formular leer]
  O -->|Fest tippen| F2[Formular mit Daten]
  O -->|„Suchen“| KI([09 KI-Suche])
  O -->|Tab Kategorien| KA([10])
  F & F2 -->|„Als Entwurf“| V1{Name vorhanden?}
  V1 -- ja --> S1[POST / PATCH · status=draft]
  F & F2 -->|„Veröffentlichen“| V2{Pflichtfelder ok?}
  V2 -- nein --> ERR[Feldfehler + Toast]
  V2 -- ja --> S2[PATCH + POST …/publish]
  S2 -. async .-> N1([Index, „Neu an deinem Wohnort“ / „Änderung“])
  F2 -->|⋯ → Absagen| DA[Dialog + Grund] --> S3[POST …/cancel]
  S3 -. async .-> N2([„Fest abgesagt“ an Favoriten + Zusagen])
  F2 -->|⋯ → Löschen| DL[Dialog] --> S4[DELETE /v1/mod/events/:id]
  O -->|„Beenden“| APP([zurück zur Nutzeransicht])
```

## Schritte

| # | Screen | Moderator-Aktion | Frontend | Backend | Modus |
|---|---|---|---|---|---|
| 1 | 08-01 | Moderator-Ansicht öffnen | Banner, Tab-Leiste, Skeleton. | `GET /v1/mod/events?region=me` (alle Status, inkl. `favoriteCount`) | sync |
| 2 | 08-01 | Suche / Status-Chip | Filtert Name und Ort. Chips mit Anzahl: Alle, Entwurf, Veröffentlicht, Vergangen, Abgesagt. | clientseitig oder `GET …?q=&status=` | lokal / sync |
| 3 | 08-05 | „+ Neues Fest“ | Leeres Formular mit Status „Entwurf“. | – | lokal |
| 4 | 08-02 | Fest öffnen | Formular mit allen Feldern, ⋯-Menü. | `GET /v1/mod/events/{id}` | sync |
| 5 | 08-03 | Ort: Adresse eingeben | Adresse wird geocodiert, die Karte springt zum Ergebnis. | `GET /v1/geocode?q=` | sync, debounced |
| 6 | 08-07 | Ort: „Pin auf Karte“ | Ein Tipp auf die Karte setzt den Pin. Ohne Adresse wird die Adresse per Reverse-Geocoding gefüllt. | `GET /v1/geocode/reverse?lat=&lon=` | sync |
| 7 | 08-04 | Programmpunkt hinzufügen/entfernen | Zeilen „Tag, Zeit“ und „Programmpunkt“. | – (wird mit dem Fest gespeichert) | lokal |
| 8 | 08-04 | „+ Hochladen“ | Auswahl aus der Mediathek. Die Kachel zeigt „Lädt hoch“, das erste Bild ist das Titelbild. | `POST /v1/mod/uploads` → signierte URL. Danach `PUT` der Datei direkt in den Speicher, dann `POST /v1/mod/events/{id}/images {uploadId}`. Thumbnails werden im Hintergrund erzeugt. | sync (Upload) + async (Thumbnails) |
| 9 | 08-04 | Bild entfernen (✕) | Entfernt die Kachel sofort. | `DELETE /v1/mod/events/{id}/images/{imageId}` | sync |
| 10 | 08-02 | „Als Entwurf“ | Pflicht ist nur der Name. Toast „Als Entwurf gespeichert“. War das Fest veröffentlicht, wird es zurückgezogen: „Zurück auf Entwurf gesetzt · für Nutzer ausgeblendet“. | `POST /v1/mod/events` (neu) bzw. `PATCH /v1/mod/events/{id}` + ggf. `POST …/unpublish` | sync |
| 11 | 08-06 | „Veröffentlichen“ mit Lücken | Rote Rahmen und Texte an den Feldern, Toast „Bitte fülle die markierten Pflichtfelder aus“. | – (Backend prüft zusätzlich: `422` mit Feldliste) | lokal / sync |
| 12 | 08-02 | „Veröffentlichen“ | Toast „Veröffentlicht · jetzt in der App sichtbar“ bzw. „Änderungen veröffentlicht“. | `PATCH …` + `POST /v1/mod/events/{id}/publish` | sync + async |
| 13 | 08-08 | ⋯ → „Fest absagen“ | Nur bei veröffentlichten Festen. Öffnet den Dialog. | – | lokal |
| 14 | 08-09 | „Absagen und benachrichtigen“ | Grund optional. Toast „Abgesagt · n Nutzer werden benachrichtigt“. | `POST /v1/mod/events/{id}/cancel {reason}` | sync + async (Fan-out) |
| 15 | 08-10 | ⋯ → „Fest löschen“ → „Endgültig löschen“ | Hinweis: Nutzer werden bei Löschung nicht benachrichtigt, Absagen ist die bessere Wahl. Toast „Fest gelöscht“. | `DELETE /v1/mod/events/{id}` (Soft-Delete; Favoriten, Listeneinträge und Einladungen werden entfernt) | sync + async (Aufräumen) |
| 16 | 08-01 | „Beenden“ | Zurück in die Nutzeransicht, Toast. Karte und Liste zeigen den neuen Stand. | `GET /v1/events` (neu laden) | sync |

## Asynchrone Folgen

| Auslöser | Event | Hintergrundarbeit |
|---|---|---|
| Veröffentlichen (erstmalig) | `event.published` | Suchindex aktualisieren. Nutzer finden, deren Wohnort im Radius liegt und die `near` aktiviert haben. Eintrag in der Liste und Push „Neu an deinem Wohnort“. |
| Änderungen veröffentlichen | `event.updated` | Bei Änderungen an Datum, Zeiten oder Ort: „Änderung“ an alle mit diesem Favoriten (`change`). |
| Absagen | `event.cancelled` | „Fest abgesagt“ mit Grund an alle mit diesem Favoriten und alle mit Zusage. Status in Zeitleisten und Listen aktualisieren. |
| Zurückziehen | `event.unpublished` | Aus dem Index entfernen, keine Benachrichtigung. |
| Löschen | `event.deleted` | Favoriten, Listeneinträge, Einladungen und Bilder entfernen. Keine Benachrichtigung. |

## Pflichtfelder und Validierung

| Feld | Entwurf | Veröffentlichen | Fehlertext |
|---|---|---|---|
| Name | ✓ | ✓ | „Bitte gib einen Namen ein.“ |
| Kategorie | – | ✓ (nur aktive) | „Bitte wähle eine Kategorie.“ |
| Beginn | – | ✓ | „Bitte wähle den Beginn.“ |
| Ende | – | ✓, ≥ Beginn | „Bitte wähle das Ende.“ / „Das Ende liegt vor dem Beginn.“ |
| Adresse oder Pin | – | ✓, innerhalb der Region | „Bitte gib eine Adresse ein oder setze einen Pin.“ |
| Öffnungszeiten, Beschreibung, Programm, Eintritt, Anfahrt, Website, Bilder | – | – | – |

## Stand der Umsetzung (R07)

- Bilder (08-04 unten) folgen in R08, die KI-Suche („Suchen“) in R10, der Tab „Kategorien“ in R09; bis dahin zeigt der Tab einen Hinweis.
- Datumsfelder nutzen die Systemauswahl (`@react-native-community/datetimepicker`, Entscheidung 01.10.2026).
- Die Status-Chips der Übersicht zeigen die Anzahl je Status und filtern auf dem Gerät.
- „Als Entwurf“ bei einem veröffentlichten Fest speichert die Änderungen und zieht das Fest danach zurück (`PATCH` + `POST …/unpublish`).
- Abgesagte Feste lassen sich nur noch in Textfeldern ändern; der Button „Als Entwurf“ entfällt dort.
- Die Benachrichtigungen aus der Tabelle „Asynchrone Folgen“ kommen mit R11; die Events werden schon jetzt über die Outbox erzeugt.

## Regeln

- Die Übersicht ist sortiert: anstehende Feste aufsteigend, danach vergangene absteigend.
- Jede Zeile zeigt Status-Pill, ggf. „Automatisch gefunden“ ([09](09-moderation-ki-suche.md)) und „♥ Anzahl Favoriten“.
- **Region:** Liegt der Pin außerhalb der eigenen Region, lehnt das Backend das Veröffentlichen mit `422 region_mismatch` ab (Annahme).
- **Gleichzeitiges Bearbeiten:** Optimistische Sperre über `version`. Bei `409` erscheint „Dieses Fest wurde inzwischen geändert“ mit der Möglichkeit, neu zu laden (Annahme).
