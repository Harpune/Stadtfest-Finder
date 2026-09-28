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

## Hinweise

- **PostGIS-Image:** `imresamu/postgis` ist der Multi-Arch-Build des PostGIS-Docker-Maintainers. Das offizielle Image hat kein ARM64 (Apple Silicon).
- **Integrationstests** (`make test`) starten eigene Container per Testcontainers, Docker muss laufen. `make test-unit` braucht kein Docker.
- **Maestro** (`make test-e2e`) erwartet einen laufenden Simulator bzw. Emulator mit installiertem Development-Build und laufendem Metro.
- **Codegen:** Nach Änderungen an `api/openapi.yaml` oder `00-docs/15-design/design/design-tokens.json` immer `make gen` ausführen und das Ergebnis committen (CI prüft auf Drift).

## Prüfung

```bash
make check
curl -s localhost:8000/v1/health/ready
```

Erwartet: `make check` ist grün, Readiness liefert `{"status":"ok","checks":{"database":"ok","redis":"ok"}}`.

## Rollback

`make deps-down` stoppt die Container. `docker compose -f infra/compose.dev.yaml down -v` löscht zusätzlich alle lokalen Daten (Datenbank, Objektspeicher).
