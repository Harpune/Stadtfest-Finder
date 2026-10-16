# Nominatim selbst hosten

## Zweck

Geocoding für PLZ-/Ortssuche (mit Autocomplete), Straßenadressen in der Moderation und Reverse-Geocoding (ADR 0006, R02). Nutzerpositionen verlassen dadurch nicht die eigene Infrastruktur. Das Backend spricht Nominatim über den Geocoding-Port an (`GEOCODING_PROVIDER=nominatim`, `NOMINATIM_URL`), die App nie direkt.

## Voraussetzungen

- HomeLab-Server (64 GB RAM, NVMe) mit **mindestens 100 GB frei** unter `${APPDATA}` für Deutschland
- Ausgehender Zugriff auf `download.geofabrik.de`
- Image `mediagis/nominatim:5.1` (feste Version, wie in `infra/compose.dev.yaml`)

## Schritte

1. **Dienst:** `stadtfest-nominatim` im HomeLab-Stack `stadtfest` (`mediagis/nominatim:5.1`, Deutschland-Extrakt, `IMPORT_STYLE=address`, `UPDATE_MODE=continuous` mit den täglichen Geofabrik-Diffs, Limit 12 GB RAM / 4 CPUs), nur im internen Netz, kein öffentlicher Port. Daten unter `${APPDATA}/stadtfest/nominatim`; die Offsite-Sicherung lässt sie aus, weil der Import wiederholbar ist. Das Datenbank-Passwort ist die Komodo-Variable `STADTFEST_NOMINATIM_DB_PASSWORD` (`openssl rand -hex 32`).
2. **Initialimport:** startet mit dem ersten Deploy des Stacks und dauert für Deutschland **mehrere Stunden**. Fortschritt: `docker logs -f stadtfest-nominatim` (bzw. Dozzle/Grafana).
3. **Backend:** Die HomeLab-Compose-Datei setzt `GEOCODING_PROVIDER=nominatim` und `NOMINATIM_URL=http://stadtfest-nominatim:8080`; `GEOCODING_TIMEOUT_SECONDS=3` steht fest im Stack. Keine Eingabe nötig.
4. **Updates:** `UPDATE_MODE=continuous` spielt die täglichen Geofabrik-Diffs automatisch ein. Nach einem Major-Update des Images den Import neu aufsetzen (Verzeichnis `${APPDATA}/stadtfest/nominatim` leeren, Stack neu deployen; mehrere Stunden ohne Geocoding).

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
docker exec stadtfest-nominatim curl -s "http://127.0.0.1:8080/search?postalcode=73430&country=de&format=jsonv2" | head -c 300
curl -s "https://stadtfest-api.herderstreet.de/v1/geocode?q=73430"
```

Die erste Anfrage liefert Aalen, die zweite `[{"label":"73430 Aalen", ...}]`. Ist Nominatim nicht erreichbar, antwortet die API mit `503 geocoding_unavailable`. Die Festsuche ist davon nicht betroffen.

## Rollback

- Den Dienst stoppen: `/v1/geocode*` antwortet mit `503`, alles andere läuft weiter.
- Nach einem fehlerhaften Update: auf das vorherige Volume bzw. die vorherige Image-Version zurückwechseln.
