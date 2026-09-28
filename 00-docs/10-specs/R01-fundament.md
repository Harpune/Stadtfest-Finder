# R01 · Fundament

| | |
|---|---|
| **Ziel** | Ein leeres, aber vollständig verdrahtetes Projekt: lokaler Stack startet mit einem Befehl, Backend und App laufen, CI prüft alles, was später geprüft werden muss. |
| **Hängt ab von** | – |
| **Quellen** | [CLAUDE.md](../../CLAUDE.md), [Architektur](../20-architecture/00-Design.pdf), [Design-Tokens](../15-design/design/design-tokens.json), [Design-Referenz](../15-design/design/design-referenz.md) |
| **Rollen** | Entwickler |

## Umfang

**Drin:** Repo-Struktur, Makefile, `compose.dev.yaml`, Backend-Skeleton (hexagonal), Worker-Skeleton, OpenAPI-Grundgerüst + Codegen, Mobile-Skeleton (Expo, expo-router, Theme, Fonts, Storybook, Jest, Maestro), CI-Pipeline, ADR- und Privacy-Grundgerüst.

**Nicht drin:** Fachliche Endpunkte, Datenbanktabellen (außer Alembic-Grundlage), Deployment (→ R16).

## User Stories

### R01-US1 · Lokaler Stack mit einem Befehl
Als Entwickler will ich mit `make dev` alle Abhängigkeiten und das Backend starten, damit ich sofort arbeiten kann.

- `infra/compose.dev.yaml` startet PostgreSQL + PostGIS, Redis, SeaweedFS (S3, ADR 0007) und Keycloak mit festen Versionen und Healthchecks.
- **Nominatim:** Standardmäßig läuft lokal ein Fake-Adapter. Optional startet ein Nominatim-Container mit kleinem Extrakt (Compose-Profil `geo`), `NOMINATIM_URL` in `.env.example`.
- Keycloak importiert beim Start einen Realm `stadtfest` mit:
  - Public Client `stadtfest-app` (Authorization Code + PKCE, Redirect `stadtfest://auth`)
  - Rollen `user`, `moderator`, `category_admin`
  - Nutzer-Attribut `region`, das per Mapper als Claim im Access-Token erscheint
  - Testnutzer (Gast gibt es nicht; `nutzer@example.test`, `moderator@example.test` mit Region `ostalb`, `katadmin@example.test`). Die Zugangsdaten stehen in der Realm-Datei im Repo, nicht in der Doku.
- `make dev` startet danach das Backend mit Reload und den Worker. Abbruch mit Ctrl+C beendet beide.
- `.env.example` dokumentiert jede Variable. `.env` ist in `.gitignore`.

### R01-US2 · Backend-Skeleton nach Architekturregeln
- Paketstruktur exakt wie in CLAUDE.md (`domain/`, `application/`, `adapters/in|out/`, `generated/`, `bootstrap/`), Python 3.12, uv.
- `bootstrap/settings.py` mit pydantic-settings. Ungültige oder fehlende Pflichtwerte brechen den Start ab und nennen den Variablennamen, aber nie den Wert.
- App-Factory in `bootstrap/`, Composition Root mit DI-Verdrahtung (Ports → Adapter). Fake-Adapter sind per Settings wählbar (`*_PROVIDER=fake` nur in `ENV=dev|test`).
- Endpunkte `GET /v1/health/live` und `GET /v1/health/ready` (prüft DB und Redis), beide in der OpenAPI-Spec.
- Einheitlicher Fehler-Handler für `{error, message, fields?}`. Unbekannte Fehler ergeben `500` ohne Stacktrace im Body.
- **Logging:** strukturiert (JSON), Request-ID pro Anfrage. Ein Log-Filter entfernt Query-Strings und Header wie `Authorization`. Ein Test stellt sicher, dass `lat`, `lon`, `q` und Tokens nicht im Log landen.
- Import-Regeln werden per Tooling geprüft (z. B. `import-linter`): `domain` importiert nichts aus FastAPI, SQLAlchemy, Pydantic, Redis oder httpx, und die Abhängigkeitsrichtung ist `adapters → application → domain`.
- Alembic eingerichtet. Die erste Migration aktiviert die Extensions `postgis`, `pg_trgm` und `unaccent`.

### R01-US3 · Worker-Skeleton
- arq-Worker als eigener Prozess (`python -m stadtfest.bootstrap.worker`), gleiche Settings und gleiche Composition Root.
- Ein Beispiel-Job `ping` mit Test beweist Enqueue → Ausführung.
- Cron-Unterstützung ist konfiguriert (Zeitzone `Europe/Berlin`) und wird ab R11 genutzt.

### R01-US4 · API-first-Werkzeugkette
- `api/openapi.yaml` (OpenAPI 3.1) enthält `info`, `servers`, das Security-Schema `bearerAuth` (JWT), das Schema `Error` und die Health-Endpunkte.
- `make gen` erzeugt:
  - Pydantic-Modelle nach `backend/src/stadtfest/generated/`
  - den TypeScript-Client inkl. TanStack-Query-Hooks nach `mobile/src/api/generated/`
  
  Werkzeugvorschlag: `datamodel-code-generator` und Orval, vor der Einführung abstimmen.
- `make lint` enthält Spectral mit Regelwerk (u. a. camelCase-Properties, `operationId` Pflicht, Fehlerantworten dokumentiert).
- CI prüft **Drift**: `make gen` und danach `git diff --exit-code`.
- CI prüft Breaking Changes mit `oasdiff` gegen `main`.

### R01-US5 · Mobile-Skeleton mit Theme
- Expo (aktuelles SDK), TypeScript strict, expo-router, TanStack Query, gts, nur iOS und Android (keine `.web.tsx`, kein `react-native-web`).
- **Theme** aus `15-design/design/design-tokens.json`:
  - Dunkel- und Hellmodus
  - Markenfarben (Amber, Rosa)
  - Moderator-Akzent (Türkis)
  - Radien, Abstände, Schatten, Bewegungsdauern
  
  Standard ist die Systemeinstellung. Eine Überschreibung im Gerät ist vorbereitet (Umschalter folgt in R06).
- Schriften: Young Serif und Outfit über `expo-font`, eingebettet (keine Laufzeit-Downloads).
- Basis-Komponenten in `src/components/` mit Story und Test:
  - `Button` (primary/secondary/ghost/danger/mod, loading, disabled)
  - `IconButton` (glass)
  - `Text`-Varianten (display, body, label, caption)
  - `Toast` + `useToast` (250 ms ein, 2,2 s sichtbar)
  - `Skeleton` (Pulsieren 1,2 s)
  - `Spinner`
- Storybook for React Native lässt sich über ein eigenes Expo-Profil starten.
- Jest + RN Testing Library laufen in `make test`.
- Ein **Maestro-Smoke-Flow** startet die App und prüft den Startscreen.
- Zentrale String-Datei `src/strings/de.ts`.

### R01-US6 · CI-Pipeline
PR-Workflow in `.github/workflows/`:
- Format-Check und Lint + Typecheck (ruff, mypy strict, gts, tsc, Spectral)
- `oasdiff` und Codegen-Drift
- Tests (unit + integration mit Testcontainers)
- Trivy und CodeQL
- AI-Review (claude-code-action)

Dazu:
- Auf `main`: Docker-Images für `api`, `worker` und `mcp` bauen (vorerst nur `api` und `worker`), Push nach GHCR mit Commit-SHA.
- `make check` führt lokal dieselben Schritte aus wie die CI.

### R01-US7 · Doku-Grundgerüst
- `00-docs/25-adr/0001-adr-verwenden.md`, dazu ADRs für bereits getroffene Grundsatzentscheidungen:
  - hexagonale Architektur und Bounded Contexts
  - Zitadel als IdP (E-01, E-07)
  - arq + Redis
  - Transactional Outbox (E-13)
  - selbst gehostetes Nominatim (E-11)
- `00-docs/20-architecture/system-architecture.md`: Markdown-Fassung des PDFs (C4-Container als Mermaid, Flows A–D). CLAUDE.md verweist darauf.
- `00-docs/30-privacy/`: Gerüste für VVT, TOMs und Löschkonzept (Tabellen leer, Struktur fest).
- `00-docs/40-operations/_template.md` (Zweck, Voraussetzungen, Schritte, Prüfung, Rollback).
- `00-docs/40-operations/lokale-entwicklung.md`.

## Tests

- Unit: Settings-Validierung (fehlende Variable → Fehler mit Namen), Fehler-Handler, Log-Filter.
- Integration: Health-Ready gegen Testcontainers (PostGIS, Redis).
- Contract: Schemathesis gegen die Health-Endpunkte (die Infrastruktur steht damit).
- Mobile: Basis-Komponenten, Theme-Umschaltung (dunkel/hell rendert die Tokens).
- E2E: Maestro-Smoke.

## Definition of Done

- [ ] `make dev`, `make gen`, `make check` und `make test-e2e` laufen auf einem frischen Checkout nach der Anleitung in `lokale-entwicklung.md`.
- [ ] Die CI ist auf einem PR komplett grün, und ein bewusst eingebauter Drift schlägt fehl.
- [ ] Import-Regeln sind aktiv und durch einen Test belegt.
- [ ] ADRs, `system-architecture.md` und Privacy-Gerüste liegen vor.

## Offene Punkte

- Codegen-Werkzeuge bestätigen (siehe README).
- Storybook: On-Device-Storybook vs. separates Expo-Profil.
