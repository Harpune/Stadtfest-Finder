# Lokale Entwicklung einrichten

## Zweck

Frischer Checkout → lauffähiger lokaler Stack (Backend, Worker, Abhängigkeiten, App im Simulator). Eingeführt mit [R01](../10-specs/R01-fundament.md).

## Voraussetzungen

| Werkzeug | Version | Hinweis |
|---|---|---|
| Docker Desktop | aktuell | mind. ~15 GB freier Speicher für Images und Volumes |
| Python | 3.12 | wird von `uv` genutzt |
| uv | ≥ 0.11 | `brew install uv` |
| Node.js | ≥ 24 | |
| pnpm | 11 | `brew install pnpm` |
| Xcode | aktuell | nur für iOS-Builds; CocoaPods braucht eine UTF-8-Locale (`export LANG=en_US.UTF-8`) |
| Android Studio | aktuell | nur für Android-Builds |
| Maestro | ≥ 2.10 | `brew tap mobile-dev-inc/tap && brew install mobile-dev-inc/tap/maestro` |

Für native Builds zusätzlich **mindestens 20 GB freien Speicher** einplanen (Pods, DerivedData, Gradle).

## Schritte

1. Repository klonen, ins Wurzelverzeichnis wechseln.
2. `make dev`:
   - legt `.env` aus `.env.example` an, falls sie fehlt
   - installiert Backend- und Mobile-Abhängigkeiten
   - startet PostGIS, Redis, SeaweedFS und Keycloak
   - wendet die Migrationen an
   - startet API (Port 8000, Reload) und Worker
   - `Ctrl+C` beendet API und Worker, die Container laufen weiter (`make deps-down` stoppt sie)
3. **App (zweites Terminal):**
   - `cd mobile && pnpm ios` (bzw. `pnpm android`) baut den Development-Build und startet ihn im Simulator.
   - Danach reicht `pnpm start`.
   - Auf einem echten Gerät `EXPO_PUBLIC_API_URL=http://<LAN-IP>:8000` setzen.
4. **Storybook:** `cd mobile && pnpm storybook:app` startet die App direkt in Storybook.

## Lokale Dienste

| Dienst | Adresse (Host) | Zugang |
|---|---|---|
| API | http://localhost:8000 (`/docs` nur außerhalb von `prod`) | – |
| PostgreSQL/PostGIS | localhost:55432 | `stadtfest` / `stadtfest` / DB `stadtfest` |
| Redis | localhost:56379 | – |
| SeaweedFS (S3) | http://localhost:58333 | Schlüssel in `infra/dev/seaweedfs/s3.json` |
| Keycloak | http://localhost:58080 | Admin `admin`/`admin`; Realm `stadtfest` |
| Nominatim (optional) | http://localhost:58088 | `docker compose -f infra/compose.dev.yaml --profile geo up -d` (Import dauert) |

- Ports lassen sich in `.env` ändern (`*_HOST_PORT`).
- **Testnutzer:** `nutzer@example.test` (Rolle `user`), `moderator@example.test` (`moderator`, Region `ostalb`), `katadmin@example.test` (`moderator`, `category_admin`). Die Passwörter stehen in `infra/dev/keycloak/stadtfest-realm.json` und gelten nur lokal.

## Anmeldung lokal (R05)

- Die App meldet sich per PKCE am lokalen Keycloak an (`EXPO_PUBLIC_AUTH_ISSUER`, Standard `http://localhost:58080/realms/stadtfest`). Das Backend prüft die Tokens gegen denselben Issuer (`AUTH_ISSUER` in `.env`). Beide Adressen müssen **gleich** sein, denn Keycloak schreibt den aufgerufenen Host in `iss`.
- **Android-Emulator:** `adb reverse tcp:58080 tcp:58080 && adb reverse tcp:8000 tcp:8000 && adb reverse tcp:58333 tcp:58333` (58333: Objektspeicher für Bild-Upload und -Anzeige, R08), dann funktioniert `localhost` auch im Emulator. **Echtes Gerät:** in `mobile/.env` und `.env` die LAN-IP statt `localhost` eintragen.
- **Kontolöschung:** `.env` enthält `IDP_ADMIN_PROVIDER=keycloak` mit dem Dev-Client `stadtfest-admin` (siehe `.env.example`). Fehlen die Variablen in einer älteren `.env`, nutzt das Backend den Fake und löscht den Keycloak-Nutzer nicht.
- **Realm aktualisieren:** Keycloak importiert `stadtfest-realm.json` nur, wenn der Realm noch nicht existiert. Nach Änderungen am Realm (z. B. dem Client `stadtfest-admin` aus R05) den Container neu anlegen: `docker compose -f infra/compose.dev.yaml up -d --force-recreate keycloak`. Lokal angelegte Nutzer gehen dabei verloren.

## Hinweise

- **PostGIS-Image:** `imresamu/postgis` ist der Multi-Arch-Build des PostGIS-Docker-Maintainers. Das offizielle Image hat kein ARM64 (Apple Silicon).
- **Integrationstests** (`make test`) starten eigene Container per Testcontainers, Docker muss laufen. `make test-unit` braucht kein Docker.
- **Maestro** (`make test-e2e`) erwartet einen laufenden Simulator bzw. Emulator mit installiertem Development-Build und laufendem Metro.
- **Echtes Android-Gerät per USB:** USB-Debugging einschalten, dann `adb reverse tcp:8081 tcp:8081`, `adb reverse tcp:8000 tcp:8000`, `adb reverse tcp:58080 tcp:58080` und `adb reverse tcp:58333 tcp:58333`. So erreicht das Gerät Metro, API, Keycloak und den Objektspeicher (SeaweedFS) unter `localhost`, und der Issuer im Token passt zum Backend. Build: `cd mobile/android && ./gradlew assembleDebug`, Installation: `adb install -r app/build/outputs/apk/debug/app-debug.apk`.
- Maestro 2.10 kann auf manchen echten Android-Geräten keinen Text eingeben (Pixel 8, Android 17: `inputText` bricht nach 120 s ab, auch mit abgeschalteten Animationen). Flows mit Texteingabe tragen das Tag `typing`; auf solchen Geräten `cd mobile && maestro test --exclude-tags typing .maestro` verwenden.
- **Codegen:** Nach Änderungen an `api/openapi.yaml` oder `00-docs/15-design/design/design-tokens.json` immer `make gen` ausführen und das Ergebnis committen (CI prüft auf Drift).

## Prüfung

```bash
make check
curl -s localhost:8000/v1/health/ready
```

Erwartet: `make check` ist grün, Readiness liefert `{"status":"ok","checks":{"database":"ok","redis":"ok"}}`.

## Rollback

`make deps-down` stoppt die Container. `docker compose -f infra/compose.dev.yaml down -v` löscht zusätzlich alle lokalen Daten (Datenbank, Objektspeicher).
