# Nominatim selbst hosten

## Zweck

Geocoding für PLZ-/Ortssuche (mit Autocomplete), Straßenadressen in der Moderation und Reverse-Geocoding (ADR 0006, R02). Nutzerpositionen verlassen dadurch nicht die eigene Infrastruktur. Das Backend spricht Nominatim über den Geocoding-Port an (`GEOCODING_PROVIDER=nominatim`, `NOMINATIM_URL`), die App nie direkt.

## Voraussetzungen

- Server mit Docker (Komodo-Stack, R16), **mindestens 8 GB RAM (empfohlen 16 GB) und 100 GB SSD** für Deutschland
- Ausgehender Zugriff auf `download.geofabrik.de`
- Image `mediagis/nominatim:5.1` (feste Version, wie in `infra/compose.dev.yaml`)

## Schritte

1. **Dienst anlegen:** Service `nominatim` im Produktions-Compose (R16), nur im internen Netz erreichbar, kein öffentlicher Port:
   ```yaml
   nominatim:
     image: mediagis/nominatim:5.1
     environment:
       PBF_URL: https://download.geofabrik.de/europe/germany-latest.osm.pbf
       REPLICATION_URL: https://download.geofabrik.de/europe/germany-updates/
       IMPORT_STYLE: address
       NOMINATIM_PASSWORD: ${NOMINATIM_DB_PASSWORD}
       UPDATE_MODE: continuous
     volumes:
       - nominatim-data:/var/lib/postgresql/16/main
     shm_size: 2gb
   ```
   `IMPORT_STYLE=address` reicht für Adressen, PLZ und Orte und spart Speicher.
2. **Initialimport** starten (`docker compose up -d nominatim`). Er dauert für Deutschland je nach Hardware **mehrere Stunden**. Fortschritt: `docker compose logs -f nominatim`.
3. **Backend konfigurieren** (Komodo-Secrets bzw. Umgebung):
   ```bash
   GEOCODING_PROVIDER=nominatim
   NOMINATIM_URL=http://nominatim:8080
   GEOCODING_TIMEOUT_SECONDS=3
   ```
4. **Updates:** `UPDATE_MODE=continuous` spielt die täglichen Geofabrik-Diffs automatisch ein. Nach einem Major-Update des Images den Import neu aufsetzen (neues Volume), erst danach umschalten.

## Lokal

- Standard ist `GEOCODING_PROVIDER=fake` (feste Orte um Aalen), kein Container nötig.
- Echte Tests mit kleinem Extrakt (Regierungsbezirk Stuttgart, Import ca. 20–40 min):
  ```bash
  docker compose -f infra/compose.dev.yaml --profile geo up -d nominatim
  ```
  Danach in `.env` `GEOCODING_PROVIDER=nominatim` und `NOMINATIM_URL=http://localhost:58088` setzen.
- **Tests** rufen Nominatim nie live auf. Sie nutzen aufgezeichnete Antworten in `backend/tests/fixtures/nominatim/`.

## Prüfung

```bash
curl -s "http://nominatim:8080/search?postalcode=73430&country=de&format=jsonv2" | head
curl -s "http://<api>/v1/geocode?q=73430"
```

Die erste Anfrage liefert Aalen, die zweite `[{"label":"73430 Aalen", ...}]`. Ist Nominatim nicht erreichbar, antwortet die API mit `503 geocoding_unavailable`. Die Festsuche ist davon nicht betroffen.

## Rollback

- Den Dienst stoppen: `/v1/geocode*` antwortet mit `503`, alles andere läuft weiter.
- Nach einem fehlerhaften Update: auf das vorherige Volume bzw. die vorherige Image-Version zurückwechseln.
