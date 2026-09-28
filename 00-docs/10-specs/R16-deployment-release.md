# R16 · Deployment und Release

| | |
|---|---|
| **Ziel** | Der Stadtfest-Finder läuft produktiv auf dem eigenen Server (EU) über Komodo. Die Apps sind über EAS gebaut und in den Stores eingereicht. Datenschutz-Doku und Betrieb sind vollständig. |
| **Hängt ab von** | alle vorherigen. **Empfehlung:** US1–US3 schon nach R05 umsetzen, dann per Inkrement erweitern. |
| **Quellen** | [CLAUDE.md „Git & CI/CD“, „External services“, „Privacy“](../../CLAUDE.md), Architektur |

## User Stories

### R16-US1 · Produktionsstack
- `infra/compose.yaml`:
  - Dienste `api`, `worker`, `mcp`, PostgreSQL + PostGIS, Redis, Nominatim (Deutschland)
  - Objektspeicher (EU-S3 oder selbst gehostetes SeaweedFS, per ADR)
  - Reverse Proxy mit TLS (Caddy oder Traefik, per ADR)
  - statische Auslieferung für die Deep-Link-Domain (R04)
- Images aus GHCR, getaggt mit Commit-SHA und SemVer. Komodo deployt eine festgelegte Version.
- Migrationen laufen als eigener Schritt vor dem Start der neuen API-Version (Alembic-Job). Nur rückwärtskompatible Migrationen bei laufendem Betrieb (Expand/Contract).
- Healthchecks und Restart-Policies für alle Dienste. Ressourcenlimits für Nominatim und Worker.

### R16-US2 · Konfiguration und Geheimnisse
- Alle Secrets liegen in Komodo bzw. GitHub Secrets, keine im Repo.
- Die Produktion startet nur mit vollständig validierten Settings (fail fast).
- Produktive Standards: `LLM_PROVIDER=mistral` oder `ollama`, `PUSH_PROVIDER` nach ADR.

### R16-US3 · Identität in Produktion
- Zitadel Cloud (EU-Region):
  - Projekt, App-Client, Rollen `user`, `moderator`, `category_admin`
  - Region-Claim (Action)
  - Apple- und Google-IdP
  - Service-User für die Kontolöschung
  - E-Mail-Absender
- Anleitung: `40-operations/zitadel.md` (aus R05) für Produktion vervollständigen.

### R16-US4 · Backups und Wiederherstellung
- Tägliches PostgreSQL-Backup (verschlüsselt, EU-Ziel), Aufbewahrung 30 Tage. Das Objektspeicher-Backup ist gleich geregelt.
- Die Wiederherstellung wird einmal geprobt und im Runbook `40-operations/backup-restore.md` dokumentiert.
- Backups enthalten personenbezogene Daten. Das Löschkonzept beschreibt, wie Löschungen gegenüber Backups wirken (Ablauf nach 30 Tagen).

### R16-US5 · Beobachtbarkeit
- Strukturierte Logs zentral einsehbar (ohne personenbezogene Daten), Fehler-Alarm bei 5xx-Rate und fehlgeschlagenen Jobs (Outbox-Rückstau, KI-Jobs, Push-Fehler).
- Werkzeug per ADR, EU bzw. selbst gehostet.

### R16-US6 · Mobile-Release
- EAS-Build-Workflow (separat von den Docker-Images) für iOS und Android, Profile `preview` und `production`.
- App-Konfiguration: Bundle-IDs, Schemes, Associated Domains / App Links, Push-Credentials.
- **Store-Anforderungen:**
  - Datenschutzangaben (Privacy Nutrition Label, Data Safety)
  - Kontolöschung in der App (R05)
  - Sign in with Apple (R05)
  - Berechtigungstexte für Standort, Fotos und Mitteilungen auf Deutsch
- Impressum und Datenschutzerklärung als Links in der App (Drawer-Fußbereich bzw. Einstieg-Screen).

### R16-US7 · Datenschutz-Doku abschließen
- VVT, TOMs und Löschkonzept vollständig und mit dem Code abgeglichen: Jede Tabelle mit personenbezogenen Daten hat Zweck, Rechtsgrundlage, Frist und Löschweg.
- Liste aller Auftragsverarbeiter mit Standort und ADR-Verweis: Zitadel, Hosting, S3, LLM-Anbieter, Web-Suche, Expo/APNs/FCM, ggf. Kartenkacheln.
- Test-Suite „DeleteAccount vollständig“: Ein Nutzer mit Daten in allen Kontexten wird gelöscht, danach findet ein Schema-Scan keine Zeile mit seiner ID.

## Tests

- Smoke-Tests nach dem Deployment: Health, `GET /v1/categories`, `GET /v1/events`, MCP `search_events`.
- Vollständige Maestro-Suite gegen einen Staging-Build: Gastsuche, Login, Favoriten, Moderator veröffentlicht, KI-Suche mit Fake-Anbieter in Staging.

## Doku/Betrieb

Runbooks: `deployment-komodo.md`, `zitadel.md`, `backup-restore.md`, `eas-build.md`, `store-release.md`, `monitoring.md`, alle nach Vorlage.

## Definition of Done

- [ ] Ein Merge auf `main` führt über GHCR und Komodo zu einer laufenden Produktionsversion. Ein Rollback auf die vorherige Version ist dokumentiert und geprobt.
- [ ] Die Apps sind als TestFlight- bzw. interne Testversion verfügbar.
- [ ] Datenschutz-Doku vollständig, der Löschtest ist grün.
