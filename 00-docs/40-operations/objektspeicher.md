# Objektspeicher für Festbilder einrichten

## Zweck

Festbilder (R08, [ADR 0011](../25-adr/0011-bildauslieferung.md)) liegen in einem S3-kompatiblen Bucket.
- **Lokal:** SeaweedFS aus `infra/compose.dev.yaml` ([ADR 0007](../25-adr/0007-objektspeicher-seaweedfs.md)).
- **Produktiv:** SeaweedFS auf dem Heimserver (EU), Dienst `seaweedfs` in `infra/compose.yaml` ([ADR 0019](../25-adr/0019-produktionsstack.md)). Öffentlich erreichbar ist nur `https://bilder.stadtfest.herderstreet.de` über Caddy: Lesen unter `public/` und signierte Uploads unter `uploads/`.

Das Backend spricht nur die S3-API. Ein Anbieterwechsel braucht keine Codeänderung.

## Voraussetzungen

- Zugriff auf den Server bzw. die Konsole des S3-Anbieters
- Für SeaweedFS: Shell im Container (`weed shell`)
- Komodo-Zugang für die Secrets der API und des Workers

## Schritte in Produktion (SeaweedFS im Stack)

1. **Identitäten:** `infra/prod/seaweedfs/s3.example.json` kopieren, für `stadtfest-backend` und `stadtfest-admin` je einen Access Key und ein Secret erzeugen (`openssl rand -hex 20` bzw. `openssl rand -hex 32`) und als `/etc/stadtfest/secrets/seaweedfs-s3.json` ablegen ([deployment-komodo.md](deployment-komodo.md), Schritt 2). Das Backend-Secret zusätzlich als Komodo-Secret `STADTFEST_S3_SECRET_ACCESS_KEY`.
2. **Bucket anlegen** (einmalig, nach dem ersten Start, im Komodo-Terminal des Stacks):
   ```bash
   docker compose exec seaweedfs sh -c 'echo "s3.bucket.create -name stadtfest-images" | weed shell -master=localhost:9333'
   ```
3. **Lifecycle für `uploads/`** (Sicherheitsnetz zu `purge_images`): Originale nach 2 Tagen löschen.
   ```bash
   docker compose exec seaweedfs sh -c 'echo "fs.configure -locationPrefix=/buckets/stadtfest-images/uploads/ -ttl=2d -apply" | weed shell -master=localhost:9333'
   ```
4. **Variablen:** `S3_ENDPOINT_URL`, `S3_PRESIGN_ENDPOINT_URL` und `S3_PUBLIC_BASE_URL` setzt `infra/compose.yaml` aus `IMAGES_HOST`; in der Stack-Umgebung stehen nur `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID` und das Secret.
5. **Backup:** Der Bucket wird täglich über die S3-API gesichert ([backup-restore.md](backup-restore.md)).

## Schritte für einen anderen S3-Anbieter

1. **Bucket anlegen:** Name `stadtfest-images`, Region in der EU.
   - Lokal legt der Worker den Bucket beim Start selbst an.
   - In Produktion wird er einmalig angelegt.
2. **Zugangsschlüssel** für das Backend erzeugen. Er braucht nur Rechte auf diesen Bucket: Lesen, Schreiben, Löschen und `HeadObject` auf alle Schlüssel, Anlegen von Buckets **nicht**.
   - SeaweedFS: Identität in `s3.json`, z. B. `"actions": ["Read:stadtfest-images", "Write:stadtfest-images", "List:stadtfest-images"]`.
3. **Öffentliches Lesen nur für `public/`:**
   - SeaweedFS: Identität `anonymous` mit `"actions": ["Read:stadtfest-images/public/*"]`. Das Sternchen ist nötig, ohne es antwortet SeaweedFS mit `403`.
   - AWS-kompatible Anbieter: Bucket-Policy `s3:GetObject` für `arn:aws:s3:::stadtfest-images/public/*`, `Principal: *`. Kein `ListBucket` für anonym.
4. **Lifecycle-Regel** (falls der Anbieter sie kennt): Objekte unter `uploads/` nach 2 Tagen löschen. Das ist ein Sicherheitsnetz zum täglichen Job `purge_images`.
5. **CORS** ist nicht nötig, weil die App nativ lädt. Für Storybook im Browser nur bei Bedarf `GET` von `*` erlauben.
6. **Secrets hinterlegen:** in Komodo für API und Worker, lokal in `.env` (siehe `.env.example`). **Niemals ins Repo.**
   - `S3_ENDPOINT_URL`: interner Endpunkt, z. B. `http://seaweedfs:8333`
   - `S3_PRESIGN_ENDPOINT_URL`: öffentlicher Endpunkt für Upload-URLs, z. B. `https://storage.example.eu`
   - `S3_PUBLIC_BASE_URL`: öffentliche Lese-URL inkl. Bucket, z. B. `https://storage.example.eu/stadtfest-images` (in Produktion `https` Pflicht)
   - `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`
7. **Reverse-Proxy** vor dem öffentlichen Endpunkt:
   - TLS, `client_max_body_size` ≥ 10 MB
   - Pfade nur `/stadtfest-images/`
   - Die Admin-Oberflächen von SeaweedFS (Master, Filer) **nicht** veröffentlichen.

## Prüfung

1. Upload-URL holen und Datei hochladen. Erwartet wird `201`, danach `200` vom PUT:
   ```bash
   curl -s -X POST "$API/v1/mod/uploads" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"contentType":"image/jpeg","sizeBytes":12345}'
   ```
2. Nach dem Anhängen ans Fest steht das Bild nach einigen Sekunden auf `ready` (`GET /v1/mod/events/{id}`).
3. `curl -I <S3_PUBLIC_BASE_URL>/public/images/<bild-id>/thumb.webp` liefert `200` und `Cache-Control: public, max-age=31536000, immutable`.
4. `curl -I <S3_PUBLIC_BASE_URL>/uploads/<upload-id>` liefert `403` oder `404`, nie `200`.
5. Worker-Log: kein `image_storage_unavailable`; der Job `purge_images` läuft täglich um 03:45 Uhr.

## Rollback

- Der Wechsel des Anbieters erfolgt nur per ENV (`S3_*`). Vorhandene Objekte vorher mit `rclone sync` oder `aws s3 sync` kopieren. Die Schlüssel bleiben gleich, die Datenbank muss nicht angepasst werden.
- Bei einem Ausfall des Speichers liefert die API `503` (`storage_unavailable`) für Uploads. Bilder werden nicht angezeigt, die App zeigt den Platzhalter. Alles andere läuft weiter.
- Fehlgeschlagene Verarbeitungen lassen sich im Formular mit „Erneut versuchen“ wiederholen, solange das Original noch da ist.
