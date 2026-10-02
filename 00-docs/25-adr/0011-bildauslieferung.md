# 0011 · Festbilder: Upload direkt in den Bucket, Auslieferung ohne CDN

- **Status:** angenommen
- **Datum:** 2026-10-02

## Kontext

Mit R08 laden Moderatoren Fotos zu Festen hoch, und alle Nutzer sehen sie in Liste und Detailgalerie. Zu entscheiden war:
- wie die Dateien in den Speicher kommen,
- in welchen Formaten und Größen sie ausgeliefert werden,
- ob dafür ein CDN nötig ist.

Fotos von Smartphones enthalten oft EXIF-Daten mit GPS-Position und Gerätedaten.

## Entscheidung

- **Upload mit signierter URL:** Die App fragt `POST /v1/mod/uploads` an und lädt die Datei per `PUT` direkt in den Objektspeicher (ADR 0007), nicht über die API.
  - Die URL gilt 10 Minuten.
  - Signiert sind auch Content-Type und exakte Größe.
  - Erlaubt sind JPEG, PNG und WebP bis 10 MB.
  - Originale liegen unter `uploads/<upload-id>` und sind nicht öffentlich lesbar.
- **Verarbeitung im Worker:** `image.uploaded` läuft über die Outbox (ADR 0005). Der Worker erledigt Folgendes:
  - Er erkennt den Typ am Inhalt (Magic Bytes über Pillow).
  - Er wendet die EXIF-Drehung an und kopiert nur die Pixel. Damit verschwinden EXIF, XMP, IPTC und ICC.
  - Er erzeugt die Varianten `full` (1.600 px), `card` (600 px) und `thumb` (200 px), jeweils als **WebP** (App) und **JPEG** (Linkvorschauen, alte Clients).
  - Danach löscht er das Original.
- **Auslieferung direkt aus dem Bucket:** Varianten liegen unter `public/images/<bild-id>/<variante>.<format>`.
  - Nur dieses Präfix ist anonym lesbar.
  - Die Schlüssel enthalten nur IDs und ändern sich nie. Darum `Cache-Control: public, max-age=31536000, immutable`.
  - Die App cacht zusätzlich auf dem Gerät (`expo-image`).
  - Es gibt **kein CDN**.
- Die öffentliche Basis-URL ist per ENV einstellbar (`S3_PUBLIC_BASE_URL`). Ein CDN oder ein Reverse-Proxy mit Cache lässt sich später ohne Codeänderung davorsetzen.

## Konsequenzen

- Die API transportiert keine großen Dateien. Uploads belasten nur Speicher und Worker.
- Bilder sind öffentlich, sobald sie verarbeitet sind, auch bei Entwürfen. Die IDs sind nicht erratbar (UUIDv4), Listen gibt es anonym nicht. Für Festfotos ist das vertretbar.
- Entfernte Bilder bleiben in Gerätecaches, bis diese verfallen. Auf dem Server sind sie sofort weg.
- Speicher pro Bild: etwa sechs kleine Dateien statt eines Originals.

## Verworfene Alternativen

- **Upload über die API (multipart):** einfacher zu autorisieren, aber große Requests durch API und Proxy. Signierte URLs sind der Standardweg bei S3.
- **Bildserver mit Größen auf Abruf (imgproxy, thumbor):** flexibel, aber ein weiterer Dienst im Betrieb. Drei feste Größen reichen für Liste, Galerie und Vorschaubilder.
- **CDN (z. B. Bunny, Cloudflare):** schneller, aber ein zusätzlicher Auftragsverarbeiter, teils außerhalb der EU. Erst nötig, wenn der Heimserver die Last nicht trägt.
