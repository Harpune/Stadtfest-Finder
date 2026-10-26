# Nominatim selbst hosten

## Zweck

Geocoding für PLZ-/Ortssuche (mit Autocomplete), Straßenadressen in der Moderation und Reverse-Geocoding (ADR 0006, R02). Nutzerpositionen verlassen dadurch nicht die eigene Infrastruktur. Das Backend spricht Nominatim über den Geocoding-Port an (`GEOCODING_PROVIDER=nominatim`, `NOMINATIM_URL`), die App nie direkt.

## Voraussetzungen

- HomeLab-Server (64 GB RAM, NVMe) mit **mindestens 100 GB frei** unter `${APPDATA}` für Deutschland
- Ausgehender Zugriff auf `download.geofabrik.de`
- Image `mediagis/nominatim:5.3` (feste Version, im HomeLab-Stack gepinnt und von Renovate angehoben; lokal nutzt `infra/compose.dev.yaml` noch `5.1`)

## Schritte

1. **Dienst:** `stadtfest-nominatim` im HomeLab-Stack `stadtfest` (`mediagis/nominatim:5.3`, Deutschland-Extrakt, `IMPORT_STYLE=address`, `UPDATE_MODE=continuous` mit den täglichen Geofabrik-Diffs, Limit 12 GB RAM / 4 CPUs), nur im internen Netz, kein öffentlicher Port. Daten unter `${APPDATA}/stadtfest/nominatim`; die Offsite-Sicherung lässt sie aus, weil der Import wiederholbar ist. Das Datenbank-Passwort ist die Komodo-Variable `STADTFEST_NOMINATIM_DB_PASSWORD` (`openssl rand -hex 32`).
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

## Fehlerbehebung

### Neustart-Schleife: `invalid BlobHeader size` oder `curl: (22) … error: 416`

**Symptom:** Der Container startet immer wieder neu. Im Log steht `Resuming transfer from byte position …` und danach entweder `curl: (22) The requested URL returned error: 416` (Neustart nach einer Minute) oder nach ca. 20 Minuten Import `ERROR: PBF error: invalid BlobHeader size (> max_blob_header_size)`.

**Ursache:** `init.sh` lädt den Extrakt mit `curl -C -` nach `/nominatim/data.osm.pbf` (im Container, kein Volume) und löscht ihn erst nach einem erfolgreichen Import. Bricht der Import ab (die Marke `import-finished` fehlt), lädt jeder Neustart die Datei „weiter“. Geofabrik ersetzt `germany-latest.osm.pbf` aber täglich:

- Ist die neue Datei größer, hängt `curl` deren Ende an die alte Datei. Die Datei ist dann kaputt und `osm2pgsql` bricht mit `invalid BlobHeader size` ab.
- Ist die lokale Datei gleich groß oder größer, antwortet Geofabrik mit `416 Range Not Satisfiable` und `curl` bricht wegen `--fail-with-body` ab.

Ein erneuter Start repariert das nie. Entscheidend ist der **erste** Abbruch.

**Ersten Abbruch suchen**, bevor etwas gelöscht wird:

```bash
docker logs stadtfest-nominatim 2>&1 | grep -nE "Killed|ERROR|FATAL|Traceback|osm2pgsql" | head -40
docker inspect stadtfest-nominatim --format '{{.State.OOMKilled}} {{json .Mounts}}'
```

Der erste `osm2pgsql`-Block ohne `ERROR` gefolgt von einem zweiten Start zeigt einen Abbruch nach dem Einlesen (Indizierung). Die Zeilen direkt vor dem zweiten `osm2pgsql version` nennen den Grund, etwa ein Deploy oder Neustart des Stacks während des mehrstündigen Imports oder `OOMKilled true`.

**Beheben:**

1. Container entfernen: `docker rm -f stadtfest-nominatim`. Damit verschwindet auch die kaputte Datei, solange `/nominatim` kein Volume ist (siehe `Mounts` oben; sonst die Datei dort löschen).
2. Den halb gefüllten Datenbank-Ordner leeren: `sudo rm -rf ${APPDATA}/stadtfest/nominatim/*`.
3. Den Stack in Komodo neu deployen und während des Imports (mehrere Stunden) nicht neu starten.

**Vorbeugen:** Statt `germany-latest.osm.pbf` einen datierten Extrakt verwenden, z. B. `PBF_URL=https://download.geofabrik.de/europe/germany-261025.osm.pbf`. Dessen Inhalt ändert sich nicht, Weiterladen ist also unschädlich. Geofabrik hält datierte Extrakte nur einige Tage (Monatserste länger) vor; für einen späteren Neuimport die URL auf ein aktuelles Datum setzen. Die `UPDATE_MODE=continuous`-Diffs holen den Stand danach automatisch nach. Noch robuster: Den datierten Extrakt einmal auf dem Host laden, gegen die zugehörige `.md5` prüfen (`md5sum -c germany-261025.osm.pbf.md5`), read-only einbinden und `PBF_PATH` statt `PBF_URL` setzen.

**Hinweis:** Die Zeile `SCP='sshpass -p … your-storagebox.de'` im Log ist kein eigenes Geheimnis. Sie steht fest im `init.sh` des Images und gehört zum öffentlichen Speicher der Image-Maintainer für die optionalen Wikipedia-Daten.

## Rollback

- Den Dienst stoppen: `/v1/geocode*` antwortet mit `503`, alles andere läuft weiter.
- Nach einem fehlerhaften Update: auf das vorherige Volume bzw. die vorherige Image-Version zurückwechseln.
