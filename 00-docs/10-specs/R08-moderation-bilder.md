# R08 · Moderation: Bilder

| | |
|---|---|
| **Ziel** | Moderatoren laden Bilder zu Festen hoch und sortieren sie. Das erste Bild ist das Titelbild. Nutzer sehen die Bilder in Karussell, Liste und Galerie. |
| **Hängt ab von** | R07 |
| **Quellen** | [08 Schritt 8–9](../15-design/workflows/08-moderation-feste.md#schritte), [Ereignisse `image.uploaded`](../15-design/backend/ereignisse-und-jobs.md), Screen 08-04 |
| **Rollen** | Moderator (eigene Region). Anzeige: alle |

## Umfang

**Drin:** Storage-Port mit S3-Adapter (MinIO lokal, EU-S3 produktiv), signierte Upload-URLs, Zuordnung, Thumbnails im Worker, Entfernen von Metadaten, Reihenfolge, Löschen, Anzeige in allen Nutzeransichten, Aufräumen verwaister Uploads.

**Nicht drin:** Übernahme von Bildern aus KI-Quellen. Sie ist bewusst ausgeschlossen (Bildrechte, siehe [09 offene Punkte](../15-design/workflows/09-moderation-ki-suche.md#offene-punkte)).

## User Stories

### R08-US1 · Bild hochladen
- Formular „Bilder“ (08-04): Raster mit 3 Spalten, erstes Bild mit Label „Titelbild“, ✕ zum Entfernen, Kachel „+ Hochladen“.
- Die Auswahl kommt aus der Mediathek (`expo-image-picker`). Die Berechtigung wird erst beim Tipp abgefragt.
- Clientseitig wird auf max. 2.560 px lange Kante verkleinert und als JPEG (Qualität 0,85) gespeichert.
- Ablauf:
  1. `POST /v1/mod/uploads {contentType, sizeBytes}` → `{uploadId, url, headers, expiresAt}`. Die signierte PUT-URL gilt 10 min. Erlaubt sind `image/jpeg`, `image/png`, `image/webp` bis 10 MB, sonst `422`.
  2. Die App lädt per `PUT` direkt in den Objektspeicher. Die Kachel zeigt „Lädt hoch“ mit Spinner.
  3. `POST /v1/mod/events/{id}/images {uploadId, position?}` → `201 {imageId, status: processing}`.
- Neue Feste müssen erst als Entwurf gespeichert sein, bevor Bilder hochgeladen werden. Die App speichert dafür automatisch einen Entwurf (Annahme).
- Höchstens 12 Bilder pro Fest, sonst `422`.

### R08-US2 · Verarbeitung im Worker
- Event `image.uploaded` → Worker:
  1. prüft den tatsächlichen Dateityp (Magic Bytes)
  2. **entfernt alle EXIF-/XMP-Metadaten** (insbesondere GPS)
  3. erzeugt die Varianten `full` (max. 1.600 px), `card` (600 px) und `thumb` (200 px) als WebP und JPEG
  4. speichert `width` und `height` und setzt `status: ready`
- Die Originaldatei wird danach gelöscht.
- Bei Fehlern: `status: failed`. Das Bild erscheint mit Fehlerkachel und „Erneut versuchen“ im Formular, Nutzer sehen es nicht.
- Die Katalog-Generation wird erhöht, wenn sich das Titelbild eines veröffentlichten Fests ändert.

### R08-US3 · Reihenfolge und Entfernen
- `PUT /v1/mod/events/{id}/images/order {imageIds[]}`: vollständige Liste, sonst `422`.
- In der App: lange drücken und ziehen (Annahme, im Design nicht gestaltet) bzw. Menü „Als Titelbild“.
- `DELETE /v1/mod/events/{id}/images/{imageId}` → `204`. Die Kachel verschwindet sofort. Die Objekte werden asynchron gelöscht.

### R08-US4 · Anzeige
- `EventSummary.coverImage` und `EventDetail.images[]` enthalten URLs der Varianten.
- Auslieferung aus einem öffentlichen, nur lesbaren Bucket-Pfad mit langen Cache-Headern (unveränderliche Schlüssel), ohne eigenes CDN.
- Die Objekt-Schlüssel enthalten nur die Bild-ID, keine Namen.
- Die App nutzt `expo-image` mit Caching und Platzhalter (gestreifte Fläche) beim Laden.

### R08-US5 · Aufräumen
- Täglicher Job: Uploads ohne Zuordnung, die älter als 24 h sind, und Bilder gelöschter Feste werden aus dem Speicher entfernt.

## Daten

`upload`: `id`, `moderator_id`, `object_key`, `content_type`, `size`, `created_at`, `consumed_at`. `event_image` aus R02 mit `status` (`processing|ready|failed`) und den Varianten-Schlüsseln.

## Datenschutz

- Metadaten werden serverseitig entfernt (Test mit einem Bild mit GPS-EXIF).
- Hinweis im Formular: „Nur Bilder hochladen, an denen du die Rechte hast. Keine erkennbaren Personen.“ (Annahme)
- TOMs: Bucket-Richtlinien (Upload nur über signierte URLs, Lesen nur `public/`-Präfix).

## Tests

- Unit: Upload-Validierung (Typ, Größe, Anzahl), Reihenfolge-Validierung.
- Integration (MinIO-Testcontainer): kompletter Roundtrip signierte URL → PUT → Zuordnung → Worker → Varianten vorhanden, EXIF entfernt, Original gelöscht. Aufräum-Job.
- Contract: Upload- und Bild-Endpunkte.
- RNTL: Bildraster (Laden, Fehler, Titelbild).

## Doku/Betrieb

- `40-operations/objektspeicher.md`: Bucket, Richtlinien, Zugangsschlüssel, EU-Region, Lifecycle-Regeln.
- ADR: Bildauslieferung direkt aus dem Bucket (ohne CDN) und Variantenformate.

## Definition of Done

- [ ] Screen 08-04 vollständig umgesetzt.
- [ ] Bilder sind in Karussell, Liste und Galerie sichtbar (01-01, 01-03, 02-01).
- [ ] Ein EXIF-GPS-Test ist grün.
